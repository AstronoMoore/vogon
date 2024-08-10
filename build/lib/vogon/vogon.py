import sys
import json
import configparser
from lasair import LasairError, lasair_client as lasair
import urllib.parse
from urllib.parse import urlencode
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
import plotly.graph_objects as go
from matplotlib.pyplot import cm
import numpy as np
import configargparse


def create_settings_template():

    settings_path = get_settings_file_path()

    content = """\
    # Settings.ini file version=0.1

    # Here we will specify some required tokens, usernames and passwords

    [API_TOKENS] ; please make a bot a https://www.wis-tns.org/bots using the '+ Add bot' button  
    tns_api_key = 

    #lasair https://lasair.readthedocs.io/en/main/about.html

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
    ATLAS_difference_images = True # set to True by default (set to false if you want undifferenced images)
    """

    # Write the content to the specified file
    with open(settings_path, 'w') as file:
        file.write(content)

    print(f'{settings_path} created successfully.')
    
def ensure_settings():
    settings_path = get_settings_file_path()
    if not os.path.exists(settings_path):
        print("Settings file not found.")
        set_setting_filepath()


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
        
    # making output sub directories 
    subdirectory_plots= os.path.join(output_dir, 'plots')
    subdirectory_data= os.path.join(output_dir, 'data')

    if not os.path.exists(subdirectory_plots):
        try:
            os.makedirs(subdirectory_plots)

            print(f"Created directory: {subdirectory_plots}")
        except OSError as e:
            print(f"Failed to create directory: {e}")
            return

    if not os.path.exists(subdirectory_data):
        try:
            os.makedirs(subdirectory_data)

            print(f"Created directory: {subdirectory_data}")
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
            type = config['TNS_API']['type']
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
    
def gaia_e_mag(g_mag):
    """
    Calculate the Gaia magnitude error based on the given G-band magnitude(s).

    This function uses a polynomial model to estimate the magnitude error for Gaia photometry. The model is derived from the study:
    https://www.aanda.org/articles/aa/pdf/2021/08/aa40735-21.pdf

    """

    g_mag = np.asarray(g_mag)

    if g_mag <= 13:
        return 0.02

    c0, c1, c2, c3, c4 = 3.43779, 1.13759, 3.44123, 6.51996, 11.45922

    e_mag = (c0 - (g_mag / c1) +
                    (g_mag / c2)**2 -
                    (g_mag / c3)**3 +
                    (g_mag / c4)**4)
        
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

def request_atlas_phot(name, ra, dec, alltime, difference):
        
    use_reduced = not difference

    if alltime is True:
        mjd_max = Time.now().mjd
        mjd_min = 0  # mjd min set sufficiently before ATLAS so we get all the data
    else:
        try:
            tns_discovery_date = Time(tns_lookup(name)['discoverydate']).mjd
            mjd_min = tns_discovery_date - 50
        except (KeyError, TypeError, ValueError) as e:
            print(f'Error retrieving discovery date: {e}')
            mjd_min = 0  # Default to 0

        mjd_max = tns_discovery_date + 500

    # Debugging: print the range of MJD
    print(f'Fetching ATLAS data between MJD {mjd_min} and {mjd_max}')

    with requests.Session() as s:
        task_id = None 
        task_requested = None 
        while not task_requested:
            baseurl = 'https://fallingstar-data.com/forcedphot'
            resp = s.post(f"{baseurl}/queue/",headers=connect_atlas(),data={'ra':ra,'dec':dec,'send_email':False,"mjd_min":mjd_min,"mjd_max":mjd_max,"use_reduced": use_reduced})
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
        result_dataframe = pd.read_csv(io.StringIO(result.replace("###", "")), sep=r'\s+')
        return result_dataframe

def fetch_atlas(ra,dec,name, alltime,difference):
    retries = 30
    task_url = request_atlas_phot(name, ra , dec, alltime,difference)

    for retry in tqdm(range(retries), desc=f"Talking to ATLAS Forced Phot Server. I will make {retries} attempts to see if the job is complete before timing out"):
        try:
            isdone, result = atlas_is_task_done(task_url)
            ATLAS_data = atlas_get_results(result)
            ATLAS_data['limit'] = False

            # Update the 'limit' column to True where the condition is met
            ATLAS_data.loc[ATLAS_data['uJy'] < 3 * ATLAS_data['duJy'], 'limit'] = True # marking all non 3sig detections as limits

            ATLAS_data = ATLAS_data[ATLAS_data['m']>0]
            ATLAS_data.insert(len(ATLAS_data.columns),'telescope','ATLAS')
            ATLAS_data = ATLAS_data.rename(columns={"F": "band"})
            ATLAS_data = ATLAS_data.rename(columns={"m": "magnitude"})
            ATLAS_data = ATLAS_data.rename(columns={"dm": "e_magnitude"})
            ATLAS_data = ATLAS_data.rename(columns={"MJD": "time"})
            ATLAS_data = ATLAS_data.filter(['time','magnitude','e_magnitude','telescope','band','limit'])

            return ATLAS_data
        
        except requests.Timeout:
            print("Request timed out.")
        
        except requests.RequestException:
            pass

        if retry < retries - 1:
            time.sleep(30)  # Add a custom sdelay between retries in the settings.ini

    return ATLAS_data

def fetch_tess(iau_name):    
    # credit to https://tess.mit.edu/public/tesstransients/pages/readme.html
    try:
        data = pd.read_csv('https://tess.mit.edu/public/tesstransients/light_curves/lc_'+iau_name+'_cleaned', delim_whitespace=True, skiprows=1)   

        data.columns
        data.columns = ('BTJD', 'TJD', 'cts_per_s', 'e_cts_per_s', 'mag', 'e_mag', 'bkg','bkg_model', 'bkg2', 'e_bkg2', 'drop')
        data = data.drop(columns=['drop']) 
        data['JD'] = data['BTJD'] + 2457000.0
        data['time'] = Time(data['JD'], format='jd').mjd
        data = data[data['e_mag'] != 99.9000]
        data.insert(len(data.columns),'telescope','TESS')
        data.insert(len(data.columns),'band','TESS')
        data = data.rename(columns={"mag": "magnitude"})
        data = data.rename(columns={"e_mag": "e_magnitude"})
        data = data.filter(['time', 'band', 'magnitude', 'e_magnitude', 'telescope'])
        return data
    
    except Exception:
        print(f"No TESS data for {iau_name} check if your object has been seen by TESS at: https://tess.mit.edu/public/tesstransients/lc_bulk/count_transients.txt")
        return None

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

def plot_vogon(tns_info, data, save_path_html=None, save_path_img=None):
    # Convert columns to numeric
    data['time'] = pd.to_numeric(data['time'], errors='coerce')
    data['magnitude'] = pd.to_numeric(data['magnitude'], errors='coerce')
    if 'e_magnitude' in data.columns:
        data['e_magnitude'] = pd.to_numeric(data['e_magnitude'], errors='coerce')

    # Classify TNS object
    TNS_classification = tns_info['object_type']['name']
    tns_name = tns_info['objname']

    # Define colors for different bands
    n_colors = len(data.band.unique())
    color_1_def = cm.plasma(np.linspace(0, 0.9, int(round((n_colors+1)/2))))
    color_2_def = cm.viridis(np.linspace(0.45, 0.9, int(round((n_colors+1)/2))))

    color_1 = iter(color_1_def)
    color_2 = iter(color_2_def)

    band_color_index = {}
    count = 0
    for filter in data.band.unique():
        if count < (n_colors / 2):
            c = next(color_1)
        else:
            c = next(color_2)
        band_color_index[filter] = f'rgba({c[0]*255},{c[1]*255},{c[2]*255},{c[3]})'
        count += 1

    traces = []

    # Trace for regular data points
    for telescope in data['telescope'].unique():
        single_scope = data[data['telescope'] == telescope]
        
        for filter in single_scope['band'].unique():
            filtered_data = single_scope[single_scope['band'] == filter]
            filtered_data = filtered_data.sort_values(by='time')

            color = band_color_index.get(filter, 'rgba(0,0,0,1)')
            marker_shape = 'circle' 

            # Plot circular markers for regular data points
            regular_data = filtered_data[filtered_data['limit'] != True]
            if not regular_data.empty:
                trace = go.Scatter(
                    x=regular_data['time'],
                    y=regular_data['magnitude'],
                    mode='markers',
                    marker=dict(
                        symbol=marker_shape,
                        size=10,
                        color=color
                    ),
                    name=f'{telescope} - {filter}',
                    error_y=dict(
                        type='data',
                        array=regular_data['e_magnitude'].fillna(0).tolist() if 'e_magnitude' in regular_data.columns else None,
                        visible=True 
                    )
                )
                traces.append(trace)

            limit_data = filtered_data[filtered_data['limit'] == True]
            if not limit_data.empty:
                limit_trace = go.Scatter(
                    x=limit_data['time'],
                    y=limit_data['magnitude'],
                    mode='markers',
                    marker=dict(
                        symbol='arrow-down',  # Downward-pointing arrow
                        size=12,
                        color='rgba(0,0,0,0)',  # Transparent fill
                        line=dict(
                            color=color,  # Edge color
                            width=2                # Edge width
                        )
                    ),
                    name=f'{telescope} - {filter} (Limit)',
                    error_y=None  # No error bars for limit points
                )
                traces.append(limit_trace)

    # Create the figure
    fig = go.Figure(data=traces)

    # Update layout
    fig.update_layout(
        title=f'{tns_name} Classification: {TNS_classification}',
        xaxis_title='MJD',
        yaxis_title='Apparent Magnitude',
        yaxis=dict(
            autorange='reversed', 
            tickformat='.2f' 
        ),
        xaxis=dict(
            tickformat='.2f'  
        )
    )

    # Show the plot
    fig.show()

    return fig

def search(tnsname):
    check_output_dir()
    TNS_info = tns_lookup(tnsname)
    surveys = identify_surveys(TNS_info)

    # reading defaults from settings.ini
    config = configparser.ConfigParser()
    config.read(get_settings_file_path())
    alltime = False
    ATLAS_difference = False
    try:
        alltime_str = config.get('default', 'alltime', fallback='False')
        ATLAS_difference_str = config.get('default', 'ATLAS_difference_images', fallback='True')
        alltime = alltime_str.lower() in ('true', 'yes', '1')
        ATLAS_difference = ATLAS_difference_str.lower() in ('true', 'yes', '1')
    except Exception as e:
        print(e)
        print('There was a problem with the settings.ini')
        return None
    
    alltime = config['default']['alltime']


    print(f'{tnsname} was observed by {surveys}')

    The_Book = [] # the book is a silly reference to HHGTTG that I decided to stick with :) 

    if 'Gaia' in surveys: 
        The_Book.append(fetch_gaia(surveys['Gaia']))
    
    if 'ZTF' in surveys: 
        The_Book.append(fetch_ztf(surveys['ZTF']))

    if 'ZTF' not in surveys:
        print('Attempting a ZTF conesearch at the location with a radius of 0.1 arcsec')
        The_Book.append(fetch_ztf_cone(TNS_info[['radeg'][0]],TNS_info[['decdeg'][0]],0.1))

    The_Book.append(fetch_atlas(TNS_info[['radeg'][0]],TNS_info[['decdeg'][0]],tnsname, alltime,ATLAS_difference))

    The_Book.append(fetch_neowise(TNS_info[['radeg'][0]], TNS_info[['decdeg'][0]]))

    TESS_result = fetch_tess(tnsname)
    if TESS_result is not None: 
        The_Book.append(TESS_result)

    combined_data = pd.concat(The_Book, ignore_index=True)

    if alltime == False:
        tns_discovery_date = Time(TNS_info['discoverydate']).mjd.item()
        mjd_min = tns_discovery_date - 50 
        mjd_max = tns_discovery_date + 500
        combined_data  = combined_data[(combined_data['time'] > mjd_min) & (combined_data['time'] < mjd_max)]

    output_dir = config.get('output', 'OUTPUT_DIR', fallback='')

    subdirectory_plots= os.path.join(output_dir, 'plots')
    subdirectory_data= os.path.join(output_dir, 'data')

    fig = plot_vogon(TNS_info, combined_data)
    fig.write_html(subdirectory_plots+'/'+tnsname+'.html')
    fig.write_image(subdirectory_plots+'/'+tnsname+'.pdf')


    combined_data.to_csv(subdirectory_data+'/'+tnsname+'.csv', index = False)


    return combined_data

if __name__ == "__main__":
    ensure_settings()
    print('Done')
