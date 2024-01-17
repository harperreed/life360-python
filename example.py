from life360 import life360
import datetime

#This is only here to make the example display nicer
def prettydate( d):
    diff = datetime.datetime.utcnow() - d
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{} days ago'.format(diff.days)
    elif s <= 1:
        return 'just now'
    elif s < 60:
        return '{} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{} minutes ago'.format(s/60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{} hours ago'.format(s/3600)

if __name__ == "__main__":

    # basic authorization hash (base64 if you want to decode it and see the sekrets)
    # this is a googleable or sniffable value. i imagine life360 changes this sometimes. 
    # authorization_token = "cFJFcXVnYWJSZXRyZTRFc3RldGhlcnVmcmVQdW1hbUV4dWNyRUh1YzptM2ZydXBSZXRSZXN3ZXJFQ2hBUHJFOTZxYWtFZHI0Vg=="
    
    # updated token on 8/1/2023 @ryanbuckner
    authorization_token = "Y2F0aGFwYWNyQVBoZUtVc3RlOGV2ZXZldnVjSGFmZVRydVl1ZnJhYzpkOEM5ZVlVdkE2dUZ1YnJ1SmVnZXRyZVZ1dFJlQ1JVWQ=="
    
    # your username and password (hope they are secure!)
    username = "email@address.com"
    password = "super long password"

    #instantiate the API
    api = life360(authorization_token=authorization_token, username=username, password=password)
    if api.authenticate():

        #Grab some circles returns json
        circles =  api.get_circles()
        
        #grab id
        id = circles[0]['id']

        #Let's get your circle!
        circle = api.get_circle(id)

        #Let's display some goodies

        print("Circle name:", circle['name'])
        print("Members (" + circle['memberCount'] + "):")
        for m in circle['members']:

            print("\tName:", m['firstName'], m['lastName'])
            print("\tLocation:" , m['location']['name'])
            print("\tLatLng:" , m['location']['latitude'] +", "+ m['location']['longitude'])
            print("\tHas been at " + str(m['location']['name']) +" since " + prettydate(datetime.datetime.fromtimestamp(int(str(m['location']['since'])))))
            print("\tBattery level:" , m['location']['battery'] +"%")
            print("\t")
    else:
        print("Error authenticating")
