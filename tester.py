import json

decoded_msg = 'Room 50 Update. {"https://raw.githubusercontent.com/axeldelaguardia/PFCC_call_lights/main/": {"filename": "neopixel.py", "action": "rename", "new_filename": "np.py"}'

if decoded_msg.startswith(f'Room 50 Update'):
    try:
        # Splitting on comma instead of dot
        update_info = json.loads(decoded_msg.split(".", 1)[1])

        for url, file_info in update_info.items():
            action = file_info.get("action")
            new_filename = file_info.get("new_filename")
            filename = file_info.get("filename")
            print(url, filename, action, new_filename)
            print('success!')
    except Exception as e:
        print(f"Error updating files: {e}")

