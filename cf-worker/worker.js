// ytclip Worker — Service Worker format
// No R2 — clips stored on Catbox.moe

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request, event));
});

async function handleRequest(request, event) {
  const url = new URL(request.url);
  const path = url.pathname;

  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // POST /api/job — Create a new clip job
    if (path === '/api/job' && request.method === 'POST') {
      const body = await request.json();
      const { url, start, end, quality, format } = body;

      if (!url) {
        return jsonResponse({ error: 'URL required' }, 400, corsHeaders);
      }

      const jobId = crypto.randomUUID();

      await YTCLIP_KV.put(`job:${jobId}`, JSON.stringify({
        id: jobId,
        url,
        start: start || '0:00',
        end: end || '',
        quality: quality || '480',
        format: format || 'mp4',
        status: 'pending',
        created_at: new Date().toISOString(),
      }));

      // Trigger GitHub Actions
      try {
        await triggerGitHubActions({
          job_id: jobId,
          url,
          start: start || '0:00',
          end: end || '',
          quality: quality || '480',
          format: format || 'mp4',
        });
      } catch (ghErr) {
        console.error('Failed to trigger GitHub Actions:', ghErr);
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
      const jobData = await YTCLIP_KV.get(`job:${jobId}`, 'json');

      if (!jobData) {
        return jsonResponse({ error: 'Job not found' }, 404, corsHeaders);
      }

      return jsonResponse(jobData, 200, corsHeaders);
    }

    // GET /api/jobs — List all jobs
    if (path === '/api/jobs' && request.method === 'GET') {
      const list = await YTCLIP_KV.list({ prefix: 'job:' });
      const jobs = [];
      for (const key of list.keys) {
        const data = await YTCLIP_KV.get(key.name, 'json');
        if (data) jobs.push(data);
      }
      jobs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      return jsonResponse({ jobs: jobs.slice(0, 50) }, 200, corsHeaders);
    }

    // POST /api/webhook — GitHub Actions calls when done
    if (path === '/api/webhook' && request.method === 'POST') {
      const body = await request.json();
      const { job_id, status, clip_url, error } = body;

      if (!job_id) {
        return jsonResponse({ error: 'job_id required' }, 400, corsHeaders);
      }

      const jobData = await YTCLIP_KV.get(`job:${job_id}`, 'json');
      if (!jobData) {
        return jsonResponse({ error: 'Job not found' }, 404, corsHeaders);
      }

      jobData.status = status || 'done';
      jobData.clip_url = clip_url || null;
      jobData.error = error || null;
      jobData.completed_at = new Date().toISOString();

      await YTCLIP_KV.put(`job:${job_id}`, JSON.stringify(jobData));

      return jsonResponse({ ok: true, job: jobData }, 200, corsHeaders);
    }

    // GET /health — Health check
    if (path === '/health') {
      return jsonResponse({ ok: true, service: 'ytclip-worker', version: '1.1.0' }, 200, corsHeaders);
    }

    // Default
    return jsonResponse({ 
      service: 'ytclip-worker',
      version: '1.1.0',
      file_host: 'catbox.moe',
      endpoints: [
        'POST /api/job — Create clip job',
        'GET /api/job/:id — Check status',
        'GET /api/jobs — List jobs',
        'POST /api/webhook — GH Actions callback',
        'GET /health — Health check',
      ]
    }, 200, corsHeaders);

  } catch (err) {
    return jsonResponse({ error: err.message, stack: err.stack }, 500, corsHeaders);
  }
}

function jsonResponse(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  });
}

async function triggerGitHubActions(inputs) {
  const token = GITHUB_TOKEN;
  const repo = GITHUB_REPO;
  
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
    body: JSON.stringify({ ref: 'main', inputs }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`GitHub API ${resp.status}: ${text}`);
  }

  return true;
}
