# test_email_agent.py
from main import run_automation
from db import get_policyholder

def test_email_agent():
    ph_id = "PH_EMAIL"
    print(f"--- Testing Email Agent for {ph_id} ---")
    
    # Run the automation flow
    run_automation(ph_id)
    
    # Verify the results in "database"
    ph_data = get_policyholder(ph_id)
    print("\n--- Final Policyholder State ---")
    print(f"Name: {ph_data.get('name')}")
    print(f"Renewal Status: {ph_data.get('renewal_status')}")
    print(f"History: {ph_data.get('history')}")
    print("---------------------------------")

if __name__ == "__main__":
    test_email_agent()
