#!/usr/bin/env python3
"""
Test script for the async preprocessing pipeline.
Tests the complete flow: upload -> job dispatch -> polling -> completion
"""
import requests
import time
import json
import tempfile
import os
import pandas as pd

# Configuration
BASE_URL = "http://localhost:8000/api"
CSV_ROWS = 20
CSV_COLS = 5

def create_test_csv():
    """Create a small test CSV file"""
    df = pd.DataFrame({
        'patient_id': range(1, CSV_ROWS + 1),
        'nom': [f'Patient_{i}' for i in range(CSV_ROWS)],
        'age': [25 + i % 50 for i in range(CSV_ROWS)],
        'diagnostic': ['Hypertension', 'Diabète', 'Asthme'] * (CSV_ROWS // 3 + 1),
        'date_visite': ['2024-01-15'] * CSV_ROWS,
    })[:CSV_ROWS]
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()
    return temp_file.name

def test_async_pipeline():
    """Test the complete async pipeline"""
    
    print("📋 Creating test CSV...")
    csv_path = create_test_csv()
    
    try:
        # Step 1: Health check
        print("\n✓ Step 1: Checking Ollama health...")
        resp = requests.get(f"{BASE_URL}/patients/preprocess/health/", timeout=5)
        health = resp.json()
        if health.get('connected'):
            print(f"  ✅ Ollama connected: {health.get('configured_model')}")
        else:
            print(f"  ⚠️  Ollama not connected: {health.get('message')}")
        
        # Step 2: Upload file and dispatch job
        print("\n✓ Step 2: Uploading file and dispatching async job...")
        with open(csv_path, 'rb') as f:
            files = {'file': f}
            resp = requests.post(f"{BASE_URL}/patients/preprocess/analyze/", files=files, timeout=10)
        
        if resp.status_code == 202:
            data = resp.json()
            preprocess_id = data.get('preprocess_id')
            print(f"  ✅ Job dispatched! ID: {preprocess_id}")
            print(f"  📊 Status: {data.get('status')}")
            print(f"  💬 Message: {data.get('message')}")
        else:
            print(f"  ❌ Unexpected status {resp.status_code}: {resp.text}")
            return
        
        # Step 3: Poll for completion
        print("\n✓ Step 3: Polling for job completion...")
        max_polls = 60  # 2 minutes max
        poll_count = 0
        while poll_count < max_polls:
            poll_count += 1
            resp = requests.get(f"{BASE_URL}/patients/preprocess/{preprocess_id}/status/", timeout=5)
            status_data = resp.json()
            
            current_status = status_data.get('status')
            progress_msg = status_data.get('progress_message', '')
            
            print(f"  Poll #{poll_count}: [{current_status}] {progress_msg}")
            
            if current_status == 'completed':
                print(f"  ✅ Job completed!")
                report = status_data.get('report', {})
                if report:
                    print(f"\n  📊 Report Summary:")
                    print(f"    - Quality Score: {report.get('summary', {}).get('quality_score', 'N/A')}")
                    print(f"    - Rows: {report.get('summary', {}).get('rows', 'N/A')}")
                    print(f"    - Columns: {report.get('summary', {}).get('columns', 'N/A')}")
                    print(f"    - Issues: {len(report.get('issues', []))}")
                    print(f"    - Recommendations: {len(report.get('recommendations', []))}")
                break
            elif current_status == 'error':
                print(f"  ❌ Job failed: {status_data.get('error', 'Unknown error')}")
                break
            
            time.sleep(2)  # Poll every 2 seconds
        
        if poll_count >= max_polls:
            print(f"  ⏱️  Timeout after {max_polls} polls")
        
        print(f"\n✅ Test completed! Total time: {poll_count * 2}s")
        
    finally:
        # Cleanup
        if os.path.exists(csv_path):
            os.remove(csv_path)
            print(f"\n🧹 Cleaned up test file")

if __name__ == '__main__':
    test_async_pipeline()
