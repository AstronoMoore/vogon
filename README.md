# Vogon: A Basic Data Aggregator for Astrophysical Transients

Vogon is a tool to simplify the most excessively complicated administrative procedure in transient astronomy.

## Installation

To use Vogon, you need to install first install the software. For example, you can install `vogon` using pip:

```bash 
pip install vogon
```

## Necessary Setup Steps

```python
from vogon import vogon

vogon.set_setting_filepath()

```
You will then be prompted to provide a directory e.g. ~/vogon_settings 

Please navigate to the setings file and add your TNS and Lasiar credentials.

## Example Data Search

Import the library and call the `search` function with your desired query. Example for SN 2023ixf:

```python
from vogon import vogon

data = vogon.search('2023ixf')
```

Vogon uses IAU names with no AT or SN prefix


## Example TNS Lookup

```python
from vogon import vogon

tns_info = vogon.tns_lookup('2023ixf')

redshift = tns_info['redshift']
discoverer = tns_info['discoverer']
```
