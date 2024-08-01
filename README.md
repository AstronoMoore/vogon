# Vogon: A Basic Data Aggregator for Astrophysical Transients

Vogon gathers, homogenises and serves public photometry to the user for a given transient source. This is a tool born out of frustration and aims to simplify the most excessively complicated administrative procedure in transient astronomy. The data returned should be regarded as quicklook only and is not intended to be publication ready. The goal is to quickly inform users of publicly available measurements and limits to enable decison making in time domain astronomy. 

Mixing fandoms but the quote “It is a capital mistake to theorize before one has data.” by Sir Arthur Conan Doyle writing for Sherlock Holmes applies to transient astornomy as it does to solving crime.


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

## Please then navigate to the setings file and add your TNS and Lasiar credentials.

You will need to make a TNS bot which is straightforward

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
