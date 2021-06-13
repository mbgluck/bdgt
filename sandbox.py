# import requests
# import json

# url = 'https://public-api.tracker.gg/v2/apex/standard/profile/origin/MamasJuices/segments/legend'
# headers = {'TRN-Api-Key': '679466e0-8843-4489-9669-5d943e33e98b'}
# # auth = HTTPBasicAuth('apikey', '1234abcd')
# # files = {'filename': open('filename','rb')}

# req = requests.get(url, headers=headers)
# j = req.json()
# for d in j['data']:
#     name = d['metadata']['name']
#     kills = d['stats']['kills']['displayValue']
#     print(f'{name:<10} {kills}')
# # test = json.loads(j)
# print(req.json())



# TEMP = "test test test %(blah)s"


# def test(**kwargs):
#     x = json.dumps(kwargs)
#     print(TEMP % {'blah':x.strip('"')})
    

# ex = '{ names.push(record.transaction_id); }'
# test(blah=ex)
# a=2
# record["   transaction_id   "].padEnd(  10  ,' ')      + 
# record["   Transaction Date "].padEnd(  10  ,' ')
drill_cols = [('transaction_id',10),('Transaction Date',15)]

def iter(x):
    for field, pad in x:
        yield f'record["{field}"].padEnd({pad}," ")'

print(' + '.join(iter(drill_cols)))

