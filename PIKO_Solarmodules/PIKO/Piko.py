import urllib.request
from lxml import html

class Piko():
    def __init__(self, host=None, username='pvserver', password='pvwr'):
        if not host.startswith('http'):
            host = 'http://'+host
        self.host = host
        self.username = username
        self.password = password

    def get_data(self):
        """returns all values as a list"""
        try:
            urllib.request.urlopen(self.host)
        except ValueError:
            return False, False, False        # URL not well formatted
            print('URL not well formatted: '+self.host)
        except urllib.request.URLError:
            return False, False, False        # URL don't seem to be alive
            print("URL don't seem to be alive: "+self.host)

        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.host, self.username, self.password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        opener = urllib.request.build_opener(handler)
        opener.open(self.host)

        urllib.request.install_opener(opener)
        response = urllib.request.urlopen(self.host)
        root = html.fromstring(response.read().strip())
        data = [v.text.strip() for v in root.xpath("//td[@bgcolor='#FFFFFF']")]
        for idx, d in enumerate(data):
            try:
                data[idx] = int(d)
            except:
                data[idx] = None
        names = ['Current power','Total energy','Daily energy','Voltage','L1 Voltage', 'String1 Current', 'L1 Power', 'String2 Voltage','L2 Voltage', 'String2 Current','L2 Power', 'String3 Voltage', 'L3 Voltage','String3 Current', 'L3 Power']
        units = ['W','kWh','kWh','V','V', 'A', 'W','V','V','A','W','V','V','A','W']
        return data, names, units

if __name__ == "__main__":
    p = Piko('stadel4')
    print(p.get_data())
