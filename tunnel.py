import subprocess
import re
import time
import os
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

backend_url = None
frontend_url = None

def run_cloudflared(port):
    """Run cloudflared tunnel and return the public URL."""
    exe = os.path.join(BASE_DIR, "cloudflared.exe")
    print(f"[cloudflared] Starting tunnel on port {port}...", flush=True)
    proc = subprocess.Popen(
        [exe, "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    for line in iter(proc.stdout.readline, ''):
        print(f"[Port {port}]: {line.strip()}", flush=True)
        match = re.search(r'https://[\w\-]+\.trycloudflare\.com', line)
        if match:
            url = match.group(0)
            print(f"[Port {port} URL]: {url}", flush=True)
            return proc, url
    return proc, None


def run_localtunnel(port):
    """Fallback: Run localtunnel and return the public URL."""
    print(f"[localtunnel] Starting tunnel on port {port}...", flush=True)
    proc = subprocess.Popen(
        ['lt', '--port', str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=True
    )
    for line in iter(proc.stdout.readline, ''):
        print(f"[Port {port}]: {line.strip()}", flush=True)
        match = re.search(r'your url is:\s+(https://\S+)', line)
        if match:
            url = match.group(1)
            print(f"[Port {port} URL]: {url}", flush=True)
            return proc, url
    return proc, None


def write_env(backend_url, frontend_url):
    """Write frontend .env.local so Vite picks up the backend URL."""
    env_path = os.path.join(FRONTEND_DIR, ".env.local")
    with open(env_path, "w") as f:
        f.write(f"VITE_API_URL={backend_url}/api/v1\n")
    print(f"[ENV] Written {env_path}", flush=True)

    # Also write tunnels.json for reference
    import json
    with open(os.path.join(BASE_DIR, "tunnels.json"), "w") as f:
        json.dump({"backend": backend_url, "frontend": frontend_url}, f, indent=2)
    print("[ENV] tunnels.json updated", flush=True)


if __name__ == "__main__":
    cloudflared_exe = os.path.join(BASE_DIR, "cloudflared.exe")
    use_cloudflared = os.path.exists(cloudflared_exe)

    if use_cloudflared:
        print("[INFO] Using cloudflared (Cloudflare Tunnel) - more stable!", flush=True)
        backend_proc, backend_url = run_cloudflared(8000)
        frontend_proc, frontend_url = run_cloudflared(5173)
    else:
        print("[INFO] cloudflared.exe not found. Falling back to localtunnel.", flush=True)
        backend_proc, backend_url = run_localtunnel(8000)
        frontend_proc, frontend_url = run_localtunnel(5173)

    if backend_url and frontend_url:
        write_env(backend_url, frontend_url)
        print(f"\n{'='*60}", flush=True)
        print(f"TUNNELS READY!", flush=True)
        print(f"   Frontend: {frontend_url}", flush=True)
        print(f"   Backend:  {backend_url}", flush=True)
        print(f"   API Docs: {backend_url}/docs", flush=True)
        print(f"{'='*60}\n", flush=True)
    else:
        print("❌ TUNNEL FAILED - could not get URL", flush=True)

    # Keep running to maintain the tunnels
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping tunnels...")
        backend_proc.terminate()
        frontend_proc.terminate()
