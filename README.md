# Vogon: A Basic Data Aggregator for Astrophysical Transients

Vogon gathers, homogenises and serves public photometry to the user for a given transient source. This is a tool born out of frustration and aims to simplify the most excessively complicated administrative procedure in transient astronomy. The data returned should be regarded as quicklook only and are not intended to be publication ready. The goal is to quickly inform users of publicly available measurements and limits to enable decison making in time domain astronomy. 

## Vogon gathers data from ATLAS, ZTF via Lasair, GAIA, TESS, and NEOWISE. Suggestions to include other surveys or sources of information are strongly encouraged.

Mixing fandoms but the quote “It is a capital mistake to theorize before one has data.” by Sir Arthur Conan Doyle writing for Sherlock Holmes applies to transient astronomy as it does to solving crime.


## Installation

You can install `vogon` from source:

```bash 
git clone https://github.com/AstronoMoore/vogon.git
cd  vogon
pip install .
```
or from pip 

```bash 
pip install vogon
```

## Necessary Setup Steps (one time)

```python
from vogon import vogon

vogon.set_setting_filepath()

```
You will then be prompted to provide a directory e.g. ~/vogon_settings 
You will not need to run this step again


## Please then navigate to the setings file and add your TNS and Lasiar credentials.

You will need to make a TNS bot which is straightforward

# Example Data Search:

Import the library and call the `search` function with your desired query. Example for SN 2023ixf:

```python
from vogon import vogon

data = vogon.search('2023ixf')
```

Vogon uses IAU names with no AT or SN prefix

## Please cite the appropriate orginal sources of the data

# Example TNS Lookup

```python
from vogon import vogon

tns_info = vogon.tns_lookup('2023ixf')

redshift = tns_info['redshift']
discoverer = tns_info['discoverer']
```
