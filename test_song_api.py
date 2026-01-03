import subprocess
import time
import requests
import os
import signal
import sys

def wait_for_server(url, retries=30):
    for i in range(retries):
        try:
            requests.get(url)
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            print(f"Waiting for server... {i+1}/{retries}")
    return False

def test_api():
    print("Starting server using start.sh...")
    # Start the server using start.sh
    # We use a process group so we can kill the shell and its children (the python app)
    # redirect stdout/stderr to avoid cluttering test output, or keep it to see server logs?
    # Keeping it might be noisy but useful for debug. Let's redirect to a file.
    with open("server.log", "w") as logfile:
        process = subprocess.Popen(
            ["bash", "start.sh"], 
            stdout=logfile, 
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
    
    base_url = "http://localhost:5000"
    
    try:
        if not wait_for_server(base_url):
            print("Server failed to start. Check server.log for details.")
            return

        print("\nServer is up. Testing /api/create/song/start...")
        api_url = f"{base_url}/api/create/song/start"
        
        # Test 1: Valid payload
        print("\n[Test Case] Sending valid lyrics payload...")
        payload = {
            "lyrics": "红旗飘飘，军号嘹亮，我们心中的歌。",
            "title": "测试红歌",
            "style": "March"
        }
        try:
            r = requests.post(api_url, json=payload)
            print(f"Status Code: {r.status_code}")
            response_data = {}
            try:
                response_data = r.json()
                print(f"Response Body: {response_data}")
            except:
                print(f"Response Text: {r.text}")
            
            if r.status_code == 200:
                print("Result: SUCCESS - Task accepted and relayed through server!")
                print(f"Task ID: {response_data.get('task_id')}")
            elif "IP" in str(response_data.get("error", "")):
                print(f"Result: RELAY WORKING BUT KIE ERROR - {response_data['error']}")
                print("Hint: Check if 8.140.228.114 is added to Kie.ai whitelist.")
            else:
                print(f"Result: FAILED - {response_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"Request failed: {e}")

    finally:
        print("\nStopping server...")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait()
            print("Server stopped.")
        except ProcessLookupError:
            print("Server process already gone.")

if __name__ == "__main__":
    test_api()
