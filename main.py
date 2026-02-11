class UserDataCollector:
    def __init__(self):
        self.user_data = []

    def collect_data(self, user_id, interaction, command, device, theme, subscription_status):
        data_entry = {
            'user_id': user_id,
            'interaction': interaction,
            'command': command,
            'device': device,
            'theme': theme,
            'subscription_status': subscription_status
        }
        self.user_data.append(data_entry)

    def view_data(self):
        return self.user_data

    def download_data(self):
        import json
        with open('user_data.json', 'w') as json_file:
            json.dump(self.user_data, json_file)

    def admin_endpoint(self):
        # Placeholder for admin endpoint logic
        pass