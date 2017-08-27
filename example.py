from life360 import life360
import datetime

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

    authorization_token = "cFJFcXVnYWJSZXRyZTRFc3RldGhlcnVmcmVQdW1hbUV4dWNyRUh1YzptM2ZydXBSZXRSZXN3ZXJFQ2hBUHJFOTZxYWtFZHI0Vg=="
    username = "email@address.com"
    password = "super long password"
    build_number = 1
    api = life360(authorization_token=authorization_token, username=username, password=password)
    if api.authenticate():

        circles =  api.get_circles()
        id = circles[0]['id']
        circle = api.get_circle(id)

        print "Circle name:", circle['name']
        print "Members (" + circle['memberCount'] + "):"
        for m in circle['members']:

            print "\tName:", m['firstName'],m['lastName']
            print "\tLocation:" , m['location']['name']
            print "\tLatLng:" , m['location']['latitude'] +", "+ m['location']['longitude']
            print "\tHas been at " +m['location']['name'] +" since " + prettydate(datetime.datetime.fromtimestamp(int(m['location']['since'])))
            print "\tBattery level:" , m['location']['battery'] +"%"
            print "\t"
    else:
        print "Error authenticating"
