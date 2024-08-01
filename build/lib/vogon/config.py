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

    settings_path = get_settings_file_path()

    content = """\
    # Here we will specify some required tokens, usernames and passwords

    [API_TOKENS] ; please make a bot a https://www.wis-tns.org/bots using the '+ Add bot' button  
    tns_api_key = 
    lasair_token = 

    [TNS_API] ; please make a bot a https://www.wis-tns.org/bots using the '+ Add bot' button  
    tns_id = 
    type = 
    name = 

    [ATLAS_FP_SERVER] ; please make an account at https://fallingstar-data.com/forcedphot/
    atlas_username = 
    atlas_pass = 

    [output] ; please specify an output directory
    output_dir =

    [default] ; by default vogon returns data from 50 days before discovery and to 500 days after discovery. By setting alltime to True the data will be returned for alltime 
    alltime = False
    ATLAS_difference_images = False # set to false by diffault since this takes considerably longer and for quicklook adds marginal utility

    """

    # Write the content to the specified file
    with open(settings_path, 'w') as file:
        file.write(content)

    print(f'{settings_path} created successfully.')
    

def get_settings_file_path():
    settings_path = load_config_path()
    if not settings_path:
        settings_path = set_setting_filepath()
    return os.path.join(settings_path, 'settings.ini')