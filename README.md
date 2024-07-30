# Vogon

Vogon is a tool to simplify the most excessively complicated administrative procedure in transient astronomy.

## Installation

To use Vogon, you need to install first install the software. For example, you can install `vogon` using pip:

```bash 
pip install vogon
``` 
## Example Data Search

Import the library and call the `search` function with your desired query. For instance:

```python
from vogon import vogon

data = vogon.search('2023ixf')
```


## Example TNS Lookup

```python
from vogon import vogon

tns_info = vogon.tns_lookup('2023ixf')

redshift = tns_info['redshift']
discoverer = tns_info['discoverer']
```
