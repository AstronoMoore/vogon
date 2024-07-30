import requests
import sys
import json
import configparser
import pandas as pd
from astropy.time import Time
from lasair import LasairError, lasair_client as lasair
import urllib.parse
from urllib.parse import urlencode
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.table import Table
import time
import os
import pandas as pd
import json
import os
import requests
import time
import io
from collections import OrderedDict
import configparser
from astropy.time import Time
import os
import pkg_resources
from vogon.config import get_settings_file_path
from vogon.config import set_setting_filepath
from tqdm import tqdm

def create_settings_template():
    template_path = pkg_resources.resource_filename('vogon', 'templates/settings_template.ini')
    
    with open(template_path, 'r') as template_file:
        template_content = template_file.read()
    
    settings_path = get_settings_file_path()
    with open(settings_path, 'w') as output_file:
        output_file.write(template_content)
    
    print(f'Template settings.ini created at {settings_path}')

def ensure_settings():
    settings_path = get_settings_file_path()
    if not os.path.exists(settings_path):
        print("Settings file not found.")
        create_settings_template()


def check_output_dir():
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Read the configuration file
    config.read(get_settings_file_path())

    # Check if [output] section exists
    if 'output' not in config:
        print("The [output] section is missing from the configuration file.")
        return

    # Check if OUTPUT_DIR is defined
    output_dir = config.get('output', 'OUTPUT_DIR', fallback='')

    # If OUTPUT_DIR is not defined, prompt the user for input
    if not output_dir:
        print("The OUTPUT_DIR is not defined in the configuration file.")
        new_dir = input("Please enter the directory path to set for OUTPUT_DIR: ").strip()

        # Expand ~ to the full home directory path
        new_dir = os.path.expanduser(new_dir)

        # Validate the user input (simple check to ensure the path is not empty)
        if not new_dir:
            print("The directory path cannot be empty.")
            return

        # Set the new output directory
        output_dir = new_dir

    # Expand ~ to the full home directory path
    output_dir = os.path.expanduser(output_dir)

    # Check if the specified directory exists, and create it if it does not
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        except OSError as e:
            print(f"Failed to create directory: {e}")
            return

    # Update the OUTPUT_DIR in the configuration file if it was newly set
    if 'OUTPUT_DIR' not in config['output'] or config.get('output', 'OUTPUT_DIR') != output_dir:
        config.set('output', 'OUTPUT_DIR', output_dir)
        try:
            # Write the updated configuration back to the file
            with open(get_settings_file_path(), 'w') as configfile:
                config.write(configfile)
            print(f"Updated OUTPUT_DIR to {output_dir} in {get_settings_file_path()}")
        except OSError as e:
            print(f"Failed to write to the configuration file: {e}")


TNS_API_URL = 'https://www.wis-tns.org/api/get/object'

def get_TNS_api_key():
    ensure_settings()
    try:
        config = configparser.ConfigParser()
        config.read(get_settings_file_path())

        if 'TNS_API_KEY' in config['API_TOKENS']:
            key = config['API_TOKENS']['TNS_API_KEY']
            return key
        else:
            print("Error: TNS API key not found in settings.ini")
            return None
    except FileNotFoundError:
        print("Error: settings.ini file not found")
        return None
    

def get_atlas_login_keys():
    ensure_settings()
    try:
        config = configparser.ConfigParser()
        config.read(get_settings_file_path())
        if 'ATLAS_FP_SERVER' in config:
            username = config['ATLAS_FP_SERVER']['ATLAS_USERNAME']
            password = config['ATLAS_FP_SERVER']['ATLAS_PASS']
            return username, password
        else:
            print("Error: ATLAS not found in settings.ini. Please check that ATLAS login details are supplied")
            return None
    except Exception as e:
        print('There was a problem with the ATLAS login keys')
        print(e)
        return None


def get_LASAIR_TOKEN():
    ensure_settings()
    """
    # fetching the token from the settings.ini file
    """
    config = configparser.ConfigParser()
    config.read(get_settings_file_path())
    return config['API_TOKENS']['LASAIR_TOKEN']

def tns_lookup(tnsname: str) -> dict:
    """
    Lookup TNS information for the given object name and cache the result.
    """
    try:
        # Load API key
        api_key = get_TNS_api_key()
        if not api_key:
            print("API key is missing")
            return None

        # Load configuration
        config = configparser.ConfigParser()
        config.read(get_settings_file_path())
        try:
            tns_id = config['TNS_API']['tns_id']
            type = config['TNS_API']['account_type']
            name = config['TNS_API']['name']
        except KeyError as e:
            print(f"Missing configuration key: {e}")
            return None

        # Set up request
        data = {
            'api_key': api_key,
            'data': json.dumps({
                "objname": tnsname,
                "objid": "",
                "photometry": "1",
                "spectra": "1"
            })
        }
        tns_agent = f'tns_marker{{"tns_id":{tns_id},"account_type":"{type}","name":"{name}"}}'
        response = requests.post(TNS_API_URL, data=data, headers={'User-Agent': tns_agent})
        response.raise_for_status()

        # Ensure response is a dictionary
        response_data = response.json()
        if not isinstance(response_data, dict):
            print("Unexpected response format")
            return None

        # Extract object info
        tns_object_info = response_data.get('data', {}).get('reply', {})
        if not isinstance(tns_object_info, dict):
            print("Unexpected format in response data")
            return None

        # Cache directory and file setup
        output_dir = config.get('output', 'OUTPUT_DIR', fallback='')
        os.makedirs(output_dir, exist_ok=True)
        cache_path = os.path.join(output_dir, 'tns_info.json')

        # Load existing cache and update with new data
        tns_cache_dict = {}
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as file:
                for line in file:
                    try:
                        entry = json.loads(line)
                        if isinstance(entry, dict):
                            objname = entry.get('objname')
                            if isinstance(objname, str):
                                tns_cache_dict[objname] = entry
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Error processing cache entry: {e}")

        # Add or update the cache with the new entry
        tns_cache_dict[tnsname] = tns_object_info

        # Write the updated cache back to file
        with open(cache_path, 'w') as file:
            for entry in tns_cache_dict.values():
                json.dump(entry, file)
                file.write('\n')

        return tns_object_info

    except Exception as e:
        print(f"Fetching TNS info caused an error: {e}")
        return None

def fetch_ztf(ztf_name):
    L = lasair(get_LASAIR_TOKEN(), endpoint = "https://lasair-ztf.lsst.ac.uk/api")

    """
    Fetch ZTF data through LASAIR.

    Args:
    - ztf_name (str): The name of the ZTF object to fetch data for.
    - api_client: An instance of the LASAIR API client.

    Returns:
    - pd.DataFrame: DataFrame containing the processed ZTF data.
    """

    try:
        # Fetch data from LASAIR
        object_list = [ztf_name]
        response = L.objects(object_list)
        
        # Create a dictionary of lightcurves
        lcs_dict = {}
        for obj in response:    
            lcs_dict[obj['objectId']] = {'candidates': obj['candidates']}
        
        # process and format
        data = pd.DataFrame(lcs_dict[obj['objectId']]['candidates'])
        data = data[data['isdiffpos']=='t']
        data_ouput = data.filter(['mjd','fid','magpsf','sigmapsf'])
        # Adding filter information
        replacement_values = {1: 'g', 2: 'r'}
        data_ouput['fid'] = data_ouput['fid'].replace(replacement_values)
        data_ouput.insert(len(data_ouput.columns),'telescope','ZTF')
        data_ouput = data_ouput.rename(columns={"fid": "band"})
        data_ouput = data_ouput.rename(columns={"magpsf": "magnitude"})
        data_ouput = data_ouput.rename(columns={"sigmapsf": "e_magnitude"})
        data_ouput = data_ouput.rename(columns={"mjd": "time"})

        return data_ouput

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def fetch_ztf_cone(ra, dec, radius):
    L = lasair(get_LASAIR_TOKEN(), endpoint = "https://lasair-ztf.lsst.ac.uk/api")
    """
    Fetch ZTF data within by cone search
    """

    try:
        # Fetch data from LASAIR with cone searchs
        response = L.cone(ra, dec, radius=radius, requestType='all')
        
        # Gather ZTF object names
        ztf_object_names = [obj['object'] for obj in response]
        
        # Fetch ZTF data for each obj
        dfs = [fetch_ztf(object_name) for object_name in ztf_object_names]
        data_output = dfs

        data_output = pd.concat(dfs, ignore_index=True)

        return data_output

    except Exception as e:
        print(f"An error occurred during ZTF cone search: {e}")
        return None
    
import numpy as np

def gaia_e_mag(g_mag):
    """
    Calculate the Gaia magnitude error based on the given G-band magnitude(s).

    This function uses a polynomial model to estimate the magnitude error for Gaia photometry. The model is derived from the study:
    https://www.aanda.org/articles/aa/pdf/2021/08/aa40735-21.pdf

    Parameters:
    g_mag (float, list, or np.ndarray): The G-band magnitude value(s). Can be a single float, a list of floats, or a NumPy array.

    Returns:
    float, list, or np.ndarray: The estimated Gaia magnitude error(s). If the input magnitude(s) is/are less than 13, a constant error value of 0.02 is returned.
    """
    # Convert input to NumPy array for vectorized operations
    g_mag = np.asarray(g_mag)

    # Define constants for the polynomial model
    if np.issubdtype(g_mag.dtype, np.number):
        c0, c1, c2, c3, c4 = 3.43779, 1.13759, 3.44123, 6.51996, 11.45922

        # Initialize error array
        e_mag = np.full_like(g_mag, 0.02, dtype=float)

        # Apply polynomial model for magnitudes >= 13
        mask = g_mag >= 13
        g_mag_valid = g_mag[mask]
        e_mag[mask] = (c0 - (g_mag_valid / c1) +
                       (g_mag_valid / c2)**2 -
                       (g_mag_valid / c3)**3 +
                       (g_mag_valid / c4)**4)
    else:
        raise ValueError("The input must be a numeric type.")

    return e_mag


def fetch_gaia(gaia_name):
    """
    Fetch GAIA data
    """
    try:

        # Encode GAIA name for URL
        website = f'http://gsaweb.ast.cam.ac.uk/alerts/alert/{gaia_name}/lightcurve.csv/'
        # Read data from URL
        data = pd.read_csv(website, skiprows=1)
                
        # Clean data
        data = data[(data['averagemag'] != 'untrusted') & data['averagemag'].notna()]
        # changing to MJD and renaming columns
        data['time'] = Time(data['JD(TCB)'], format='jd').mjd
        data['band'] = 'G'
        data['telescope'] = 'Gaia'
        data.rename(columns={"averagemag": "magnitude"},inplace=True)
        # Calculate Gaia error in the magnitudes
        data['e_magnitude'] = data.apply(lambda row: gaia_e_mag(float(row['magnitude'])), axis=1)
        # filtering columns
        data = data.filter(['time', 'band', 'magnitude', 'e_magnitude', 'telescope'])
        
        return data
    except Exception as e:
        print(f"An error occurred while fetching GAIA data: {e}")
        return None
    
def fetch_neowise(ra, dec):    
    skycoord = SkyCoord(ra,dec,unit="deg")
    url =  "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?catalog=neowiser_p1bs_psd&spatial=cone&radius=5&radunits=arcsec&objstr=" + skycoord.ra.to_string(u.hour, alwayssign=True) + '+' + skycoord.dec.to_string(u.degree, alwayssign=True) + "&outfmt=1&selcols=ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro"
    r = requests.get(url)
    table = Table.read(url, format='ascii')
    neowise_master = table.to_pandas()
    neowise_w1 = neowise_master.filter(['mjd','w1mpro','w1sigmpro'])
    neowise_w1.insert(len(neowise_w1.columns),'band','w1')
    neowise_w1 = neowise_w1.rename(columns={"w1mpro": "magnitude"})
    neowise_w1 = neowise_w1.rename(columns={"w1sigmpro": "e_magnitude"})
    neowise_w2 = neowise_master.filter(['mjd','w2mpro','w2sigmpro'])
    neowise_w2.insert(len(neowise_w2.columns),'band','w2')
    neowise_w2 = neowise_w2.rename(columns={"w2mpro": "magnitude"})
    neowise_w2 = neowise_w2.rename(columns={"w2sigmpro": "e_magnitude"})
    neowise = pd.concat((neowise_w1,neowise_w2))
    neowise.insert(len(neowise.columns),'telescope','NEOWISE')
    neowise = pd.concat((neowise_w1,neowise_w2))
    neowise.insert(len(neowise.columns),'telescope','NEOWISE')
    neowise = neowise.rename(columns={"mjd": "time"}).dropna()
    
    return neowise

def connect_atlas():

    ATLAS_USERNAME, ATLAS_PASS = get_atlas_login_keys()

    atlas_url = 'https://fallingstar-data.com/forcedphot'
    
    with requests.Session() as s:
        response = s.post(
            url=f"{atlas_url}/api-token-auth/",
            data={'username': ATLAS_USERNAME, 'password': ATLAS_PASS}
        )

        if response.status_code == 200:
            token = response.json()['token']
            headers = {
                'Authorization': f'Token {token}',
                'Accept': 'application/json'
            }
            return headers
        else:
            raise RuntimeError(f'ERROR in connect_atlas(): {response.status_code}')

def atlas_new_task_ledger(name, task_url, result_url, complete_flag, results_fetched, cleaned):

    check_output_dir()
    config = configparser.ConfigParser()
    config.read(get_settings_file_path())
    # Check if OUTPUT_DIR is defined
    output_dir = config.get('output', 'OUTPUT_DIR', fallback='')

    # check if ATLAS ledger exists 
    if not os.path.exists(output_dir + '/atlas_task_list.json'):
        # Create an empty file
        with open(output_dir + '/atlas_task_list.json', 'w') as file:
            pass  # This will create an empty file



    task_data = {
        'name': name,
        'task_url': task_url,
        'result_url': result_url,
        'complete_flag': complete_flag,
        'results_fetched': results_fetched,
        'cleaned': cleaned
        }
    
    # Load existing tasks from the file
    existing_tasks = []
    try:
        with open(output_dir + '/atlas_task_list.json', 'r') as file:
            existing_tasks = [json.loads(line) for line in file]
    except FileNotFoundError:
        print('need to make an atlas tast list ledger')
        pass


    # Check if task with the same name exists
    task_exists = False
    for idx, task in enumerate(existing_tasks):
        if task['name'] == name:
            # Delete existing task
            del existing_tasks[idx]
            task_exists = True
            break
    
    # Add the new task to the list
    existing_tasks.append(task_data)
    
    # Write updated task list back to file
    with open(output_dir + '/atlas_task_list.json', 'w') as file:
        for task in existing_tasks:
            json.dump(task, file)
            file.write('\n')

def request_atlas_phot(name, ra,dec, alltime):
    if alltime == True:
        mjd_max = Time.now().mjd
        mjd_min = 0
    else: 
        tns_discovery_date = Time(tns_lookup(name)['discoverydate']).mjd.item()
        mjd_min = tns_discovery_date - 50 
        mjd_max = Time.now().mjd + 500

    with requests.Session() as s:
        task_id = None 
        task_requested = None 
        while not task_requested:
            baseurl = 'https://fallingstar-data.com/forcedphot'
            resp = s.post(f"{baseurl}/queue/",headers=connect_atlas(),data={'ra':ra,'dec':dec,'send_email':False,"mjd_min":mjd_min,"mjd_max":Time.now().mjd,"use_reduced": True})
            if resp.status_code == 201:
                task_url = resp.json()['url']
                task_requested = True

        result_url = None
        complete_flag = False
        results_fetched = False
        cleaned = False
        name, task_url, result_url, complete_flag, results_fetched, cleaned
        atlas_new_task_ledger(name = name,task_url = task_url, result_url = result_url, complete_flag = complete_flag, results_fetched = results_fetched, cleaned= cleaned)
        return(task_url)
    
def atlas_task_info(task_url):
    with requests.Session() as s:
        resp = s.get(task_url, headers=connect_atlas()).json()
        return(resp)
    
def atlas_is_task_done(task_url):
    with requests.Session() as s:
        resp = s.get(task_url, headers=connect_atlas()).json()
        if resp['result_url'] is None:
            return(False, None)
        if resp['result_url'] is not None:
            return(True, resp['result_url'])
        
def atlas_get_results(result_url):
    cwd = os.getcwd()
    with requests.Session() as s:
        result = s.get(result_url, headers=connect_atlas()).text
        result_dataframe = pd.read_csv(io.StringIO(result.replace("###", "")), sep='\s+')
        return result_dataframe

def fetch_atlas(ra,dec,name, alltime):
    retries = 20
    task_url = request_atlas_phot(name, ra , dec, alltime)

    for retry in tqdm(range(retries), desc=f"Talking to ATLAS Forced Phot Server. There will be {retries} attempts to see if the job is complete before timing out"):
        try:
            isdone, result = atlas_is_task_done(task_url)
            ATLAS_data = atlas_get_results(result)
            ATLAS_data = ATLAS_data[ATLAS_data['m']>0]
            ATLAS_data.insert(len(ATLAS_data.columns),'telescope','ATLAS')
            ATLAS_data = ATLAS_data.rename(columns={"F": "band"})
            ATLAS_data = ATLAS_data.rename(columns={"m": "magnitude"})
            ATLAS_data = ATLAS_data.rename(columns={"dm": "e_magnitude"})
            ATLAS_data = ATLAS_data.rename(columns={"MJD": "time"})
            ATLAS_data = ATLAS_data.filter(['time','magnitude','e_magnitude','telescope','band'])

            return ATLAS_data
        
        except requests.Timeout:
            print("Request timed out.")
        
        except requests.RequestException:
            pass

        if retry < retries - 1:
            time.sleep(30)  # Add a custom sdelay between retries in the settings.ini

    return ATLAS_data

def identify_surveys(TNS_information):
    reporting_list = TNS_information['internal_names']
    reporting_list= reporting_list.split(',')
    survey_dict = {}

    # Iterate over each string in the list
    for internal_name in reporting_list:
        if 'ATLAS' in internal_name:
            survey_dict['ATLAS'] = internal_name.replace(" ", "") # removing the annoying space before the internal name  
        if 'Gaia' in internal_name:
            survey_dict['Gaia'] = internal_name.replace(" ", "")# removing the annoying space before the internal name 
        if 'ZTF' in internal_name:
            survey_dict['ZTF'] = internal_name.replace(" ", "")# removing the annoying space before the internal name 
        if 'PS' in internal_name:
            survey_dict['PS'] = internal_name.replace(" ", "")# removing the annoying space before the internal name 
        if 'GOTO' in internal_name:
            survey_dict['GOTO'] = internal_name.replace(" ", "")# removing the annoying space before the internal name 
        if 'BGEM' in internal_name:
            survey_dict['BGEM'] = internal_name
    return survey_dict

def search(tnsname):
    TNS_info = tns_lookup(tnsname)
    surveys = identify_surveys(TNS_info)

    # reading defaults from settings.ini
    config = configparser.ConfigParser()
    config.read(get_settings_file_path())
    try:
        alltime = config['default']['alltime']
    except Exception as e:
        print('There was a problem with the settings.ini')
        return None


    print(f'{tnsname} was observed by {surveys}')

    The_Book = []

    if 'Gaia' in surveys: 
        The_Book.append(fetch_gaia(surveys['Gaia']))
    
    if 'ZTF' in surveys: 
        The_Book.append(fetch_ztf(surveys['ZTF']))

    if 'ZTF' not in surveys:
        print('Attempting a ZTF conesearch at the location with a radius of 0.1 arcsec')
        The_Book.append(fetch_ztf_cone(TNS_info[['radeg'][0]],TNS_info[['decdeg'][0]],0.1))

    The_Book.append(fetch_atlas(TNS_info[['radeg'][0]],TNS_info[['decdeg'][0]],tnsname, alltime))

    The_Book.append(fetch_neowise(TNS_info[['radeg'][0]], TNS_info[['decdeg'][0]]))

    combined_data = pd.concat(The_Book, ignore_index=True)

    if alltime == True:
        pass
    else: 
        tns_discovery_date = Time(TNS_info['discoverydate']).mjd.item()
        mjd_min = tns_discovery_date - 50 
        mjd_max = Time.now().mjd + 500

        combined_data  = combined_data[(combined_data['time'] > mjd_min) & (combined_data['time'] < mjd_max)]

    return combined_data

if __name__ == "__main__":
    ensure_settings()
    print('Done')
