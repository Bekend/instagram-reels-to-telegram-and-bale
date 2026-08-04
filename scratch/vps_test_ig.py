import paramiko

VPS_IP = "148.135.207.189"
VPS_USER = "root"
VPS_PASS = "Farzad1383"

def run_vps_ig_test():
    print("Connecting to VPS to run live Instagram fetch test...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=15)
    
    cmd = """
cd /root/instagram_reels_telegram_bot
/usr/bin/python3 -c "import database as db, instagram_fetcher as ig; s = db.get_settings(); print('SessionID present:', bool(s.get('instagram_session_id'))); reels = ig.get_algorithmic_reels(session_id=s.get('instagram_session_id'), username=s.get('instagram_username'), password=s.get('instagram_password'), max_items=5); print('Reels fetched:', len(reels)); print('Sample:', [r.get('reel_id') for r in reels])"
"""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', 'ignore')
    err = stderr.read().decode('utf-8', 'ignore')
    print("VPS Test STDOUT:\n", out)
    if err:
        print("VPS Test STDERR:\n", err)
    ssh.close()

if __name__ == "__main__":
    run_vps_ig_test()
