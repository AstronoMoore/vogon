import os
import json
import pkg_resources


CONFIG_FILE = os.path.expanduser('~/.settings.ini')

def save_config_path(path):
    config = {'settings_path': path}
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_config_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('settings_path')
    return None

def set_setting_filepath():
    path = input("Enter the directory where you want to save the settings file: ")
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    save_config_path(path)
    create_settings_template()
    return path

def create_settings_template():
    template_path = pkg_resources.resource_filename('vogon', 'templates/settings_template.ini')
    
    with open(template_path, 'r') as template_file:
        template_content = template_file.read()
    
    settings_path = get_settings_file_path()
    with open(settings_path, 'w') as output_file:
        output_file.write(template_content)

def get_settings_file_path():
    settings_path = load_config_path()
    if not settings_path:
        settings_path = set_setting_filepath()
    return os.path.join(settings_path, 'settings.ini')