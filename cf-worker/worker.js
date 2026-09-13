// ytclip Worker — Cloudflare Worker for job queue management
// Handles: create job, check status, serve clips from R2, trigger GitHub Actions

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers for browser access
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // ── API Routes ────────────────────────────────────────────────────
      
      // POST /api/job — Create a new clip job
      if (path === '/api/job' && request.method === 'POST') {
        const body = await request.json();
        const { url, start, end, quality, format } = body;

        if (!url) {
          return jsonResponse({ error: 'URL required' }, 400, corsHeaders);
        }

        // Generate job ID
        const jobId = crypto.randomUUID();

        // Store job in KV
        await env.YTCLIP_KV.put(`job:${jobId}`, JSON.stringify({
          id: jobId,
          url,
          start: start || '0:00',
          end: end || '',
          quality: quality || '480',
          format: format || 'mp4',
          status: 'pending',
          created_at: new Date().toISOString(),
        }));

        // Trigger GitHub Actions workflow
        try {
          await triggerGitHubActions(env, {
            job_id: jobId,
            url,
            start: start || '0:00',
            end: end || '',
            quality: quality || '480',
            format: format || 'mp4',
          });
        } catch (ghErr) {
          console.error('Failed to trigger GitHub Actions:', ghErr);
          // Job is still created, GH might be rate-limited
        }

        return jsonResponse({ 
          job_id: jobId, 
          status: 'pending',
          poll_url: `/api/job/${jobId}`,
          message: 'Job created. Processing on GitHub Actions.'
        }, 200, corsHeaders);
      }

      // GET /api/job/:id — Check job status
      if (path.startsWith('/api/job/') && request.method === 'GET') {
        const jobId = path.split('/').pop();
        const jobData = await env.YTCLIP_KV.get(`job:${jobId}`, 'json');

        if (!jobData) {
          return jsonResponse({ error: 'Job not found' }, 404, corsHeaders);
        }

        return jsonResponse(jobData, 200, corsHeaders);
      }

      // GET /api/jobs — List all jobs (for debugging)
      if (path === '/api/jobs' && request.method === 'GET') {
        const list = await env.YTCLIP_KV.list({ prefix: 'job:' });
        const jobs = [];
        for (const key of list.keys) {
          const data = await env.YTCLIP_KV.get(key.name, 'json');
          if (data) jobs.push(data);
        }
        // Sort by created_at descending
        jobs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        return jsonResponse({ jobs: jobs.slice(0, 50) }, 200, corsHeaders);
      }

      // POST /api/webhook — GitHub Actions calls when job is done
      if (path === '/api/webhook' && request.method === 'POST') {
        const body = await request.json();
        const { job_id, status, clip_url, error } = body;

        if (!job_id) {
          return jsonResponse({ error: 'job_id required' }, 400, corsHeaders);
        }

        const jobData = await env.YTCLIP_KV.get(`job:${job_id}`, 'json');
        if (!jobData) {
          return jsonResponse({ error: 'Job not found' }, 404, corsHeaders);
        }

        jobData.status = status || 'done';
        jobData.clip_url = clip_url || null;
        jobData.error = error || null;
        jobData.completed_at = new Date().toISOString();

        await env.YTCLIP_KV.put(`job:${job_id}`, JSON.stringify(jobData));

        return jsonResponse({ ok: true, job: jobData }, 200, corsHeaders);
      }

      // GET /api/r2/:key — Serve clip from R2
      if (path.startsWith('/api/r2/') && request.method === 'GET') {
        const key = decodeURIComponent(path.replace('/api/r2/', ''));
        const object = await env.YTCLIP_R2.get(key);

        if (!object) {
          return jsonResponse({ error: 'File not found' }, 404, corsHeaders);
        }

        const headers = new Headers();
        object.writeHttpMetadata(headers);
        headers.set('etag', object.etag);
        headers.set('Access-Control-Allow-Origin', '*');
        
        return new Response(object.body, { headers });
      }

      // ── Health check ──────────────────────────────────────────────────
      if (path === '/health') {
        return jsonResponse({ ok: true, service: 'ytclip-worker' }, 200, corsHeaders);
      }

      // Default response
      return jsonResponse({ 
        service: 'ytclip-worker',
        version: '1.0.0',
        endpoints: [
          'POST /api/job — Create clip job',
          'GET /api/job/:id — Check status',
          'GET /api/jobs — List jobs',
          'POST /api/webhook — GH Actions callback',
          'GET /api/r2/:key — Download clip',
          'GET /health — Health check',
        ]
      }, 200, corsHeaders);

    } catch (err) {
      return jsonResponse({ error: err.message, stack: err.stack }, 500, corsHeaders);
    }
  }
};

// ── Helper Functions ────────────────────────────────────────────────────

function jsonResponse(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
  });
}

async function triggerGitHubActions(env, inputs) {
  const token = env.GITHUB_TOKEN;
  const repo = env.GITHUB_REPO; // format: "owner/repo"
  
  if (!token || !repo) {
    throw new Error('GITHUB_TOKEN or GITHUB_REPO not configured');
  }

  const apiUrl = `https://api.github.com/repos/${repo}/actions/workflows/process-clip.yml/dispatches`;
  
  const resp = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/vnd.github.v3+json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ref: 'main',
      inputs,
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`GitHub API ${resp.status}: ${text}`);
  }

  return true;
}
