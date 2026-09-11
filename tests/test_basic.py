#!/usr/bin/env python3
"""Test ytclip basic functionality"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ytclip import validate_url, get_video_id, parse_timestamp

def test_validate_url():
    valid = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/abc123",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ]
    invalid = [
        "https://google.com",
        "not a url",
        "https://vimeo.com/123",
    ]
    
    for url in valid:
        assert validate_url(url), f"Should be valid: {url}"
    for url in invalid:
        assert not validate_url(url), f"Should be invalid: {url}"
    print("✅ URL validation passed")

def test_get_video_id():
    assert get_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert get_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert get_video_id("https://youtube.com/shorts/abc123") == "abc123"
    print("✅ Video ID extraction passed")

def test_parse_timestamp():
    assert parse_timestamp("1:30") == 90.0
    assert parse_timestamp("0:05") == 5.0
    assert parse_timestamp("1:00:00") == 3600.0
    assert parse_timestamp("1:30:45") == 5445.0
    print("✅ Timestamp parsing passed")

if __name__ == '__main__':
    test_validate_url()
    test_get_video_id()
    test_parse_timestamp()
    print("\n✅ All tests passed!")
