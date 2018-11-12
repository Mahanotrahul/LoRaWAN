import requests
import json
import base64

url = "http://168.87.87.213:8080/davc/m2m/HPE_IoT/9c65f9fffe218a69//default"

querystring = {"ty":"4","lim":"100"}

headers = {
    'content-type': "application/vnd.onem2m-res+json;ty=4;",
    'x-m2m-origin': "C73773960-b9dff09a",
    'x-m2m-ri': "9900001",
    'accept': "application/vnd.onem2m-res+json;",
    'authorization': "Basic QzczNzczOTYwLWI5ZGZmMDlhOlRlc3RAMTIz",
    'cache-control': "no-cache",
    'postman-token': "da948708-1349-ecf8-113e-87fe89453425"
    }

response = requests.request("GET", url, headers=headers, params=querystring)


load_data = json.loads(response.text)
print("Length of the Response Array : " + str(len(load_data)))

file = open("Data.csv", "w+")
print(file.name)

for i in range(len(load_data)):
    print(str(i) + ": ")
    try:
        dataFrame = base64.b64decode(json.loads(load_data[i]["m2m:cin"]["con"])["payloads_ul"]["dataFrame"]).decode("utf-8")
        timestamp = json.loads(load_data[i]["m2m:cin"]["con"])["payloads_ul"]["timestamp"]
        file.write(dataFrame + " , " + timestamp + "\n")
        print("Mass : " + dataFrame + " gram")
        print("Timestamp : " + timestamp)
    except Exception as e:
        print(e)
        print("Exception Occurred")
    print("")


file.close()