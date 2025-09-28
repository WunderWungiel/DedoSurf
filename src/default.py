import appuifw2 as appuifw
import e32
import urllib
import graphics
import os
import re
import sysinfo
import zipfile
import simplejson as json

# Use e32.drive_list() to retrieve drives list
def get_drive():
    drives = e32.drive_list()
    # Remove Z and Y
    for letter in [u"Z:", u"Y:"]:
        if letter in drives:
            drives.remove(letter)
    return drives[-1] + "\\Dedomil"

dl_path = get_drive()

if not os.path.isdir(dl_path):
    os.mkdir(dl_path)
if not os.path.isdir(os.path.join(dl_path, "screenshots")):
    os.mkdir(os.path.join(dl_path, "screenshots"))

class API:
    def __init__(self):
        self.api_url = "http://192.168.1.5:8080/api/v1/"

    def get_resolutions(self, id):
        r = urllib.urlopen(self.api_url + "get_resolutions/?id=%s" % id)
        return json.loads(r.read().decode("utf-8"))

    def get_app_info(self, link):
        r = urllib.urlopen(self.api_url + "get_app_info/?link=%s" % link)
        return json.loads(r.read().decode("utf-8"))

    def search(self, query, page):
        r = urllib.urlopen(self.api_url + "search/?q=%s&page=%s" % (query, page))
        return json.loads(r.read().decode("utf-8"))

    def retrieve_games(self, link):
        r = urllib.urlopen(self.api_url + "retrieve_games/?link=%s" % link)
        return json.loads(r.read().decode("utf-8"))

api = API()

# One liner to grab resolution of device into string in <width>x<height> format
device_res = 'x'.join([str(res) for res in sysinfo.display_pixels()])

class GameDescriptionView(appuifw.View):
    def __init__(self, gameinfo):
        appuifw.View.__init__(self)
                
        self.app_title = gameinfo["title"]
        self.description = gameinfo["description"]
        self.date = gameinfo["date"]
        self.counter = gameinfo["counter"]
        self.download_links = gameinfo["download_links"]
        self.vendor = gameinfo["vendor"]
        self.splash = gameinfo["splash"]
        self.screenshot = gameinfo["screenshots"]
                
        # View Properties
        self.exit_key_text = u"Back"
        self.menu = default_menu
        self.set_tabs([u"Info", u"Screenshots", u"Description", u"Links"], self.handle_tab)
        self.title = u'Info | %s' % self.app_title
        self.body = self.app_simple_info()
        # End of View Properties

    def app_simple_info(self):
        simple_info_app = appuifw.Text(scrollbar=True, skinned=True)
        simple_info_app.font = (u"Nokia Sans S60", 25)
        simple_info_app.style = appuifw.STYLE_BOLD
        simple_info_app.add(self.app_title)
        simple_info_app.font = (u"Nokia Sans S60", 15)
        simple_info_app.add("\n\nAdded: %s" % self.date)
        simple_info_app.add("\n\nDownloads: %s" % self.counter)
        simple_info_app.add("\n\nVendor: %s" % self.vendor)
        return simple_info_app

    def app_description(self):
        description_app = appuifw.Text(scrollbar=True, skinned=True)
        description_app.font = (u"Nokia Sans S60", 13)
        description_app.add("\n\nDescription: %s" % self.description)
        return description_app

    class AppScreenshots:
        def __init__(self, description_ref):
            self.skip = None
            link = description_ref.screenshot
            if not link:
                self.skip = True
            parts = link.split('/')
            filename = parts[-1]
            path = os.path.join(dl_path, "screenshots", filename)
            if not os.path.isfile(path):
                r = urllib.urlopen(link)
                f = open(path, "wb")
                f.write(r.read())
                f.close()
            self.path = path

        def handle_redraw(self, rect):
            self.screenshots_app.blit(self.myimage, scale=self.scale)

        def run(self):
            if self.skip:
                text_app = appuifw.Text(skinned=True)
                return text_app
            try:
                self.myimage = graphics.Image.open(self.path)
                self.screenshots_app = appuifw.Canvas(event_callback=None, redraw_callback=self.handle_redraw)
                self.scale = 0
                return self.screenshots_app      
            except SymbianError:
                text_app = appuifw.Text(skinned=True)
                return text_app

    class Download:
        def __init__(self, links, description_ref):
            self.links = links
            self.description_ref = description_ref

            links_names = []
            links_links = []

            for key, value in links.items():
                if key.find(description_ref.app_title) != -1:
                    key = key.replace(description_ref.app_title, '').strip()
                links_names.append(key)
                links_links.append(value.get('link'))

            self.links_names = links_names
            self.links_links = links_links

        def handler(self):
            index = self.download_app.current()
            link = self.links_links[index]
            try:
                response = urllib.urlopen(link)
            except urllib.HTTPError:
                appuifw.note(u"Error while downloading game", "error")
                return
            except urllib.URLError:
                appuifw.note(u"Error while downloading game", "error")
                return
            content_disposition = response.headers.get("Content-Disposition")
            filename = re.findall("filename=(.+)", content_disposition)[0]
            filename = filename.replace('"', '')
            path = os.path.join(dl_path, filename)

            appuifw.note(u"Wait... Downloading %s" % filename)
            f = open(path, "wb")
            while True:
                chunk = response.read(1024)
                if not chunk:
                    break
                f.write(chunk)
            f.close()

            full_jar_path = None
            interrupted = False
            if filename.endswith(".zip"):
                zip_file = zipfile.ZipFile(path, 'r')
                for name in zip_file.namelist():
                    if name.endswith(".jar"):
                        full_jar_path = os.path.join(dl_path, name)
                        extracted = open(full_jar_path, "wb")
                        try:
                            extracted.write(zip_file.read(name))
                            extracted.close()
                        except MemoryError:
                            interrupted = True
                            extracted.close()
                            break
                        break
                zip_file.close()
            if interrupted:
                os.remove(full_jar_path)
                file_opener.open(path)
            elif not full_jar_path and not interrupted:
                file_opener.open(path)
            elif full_jar_path and not interrupted:
                os.remove(path)
                file_opener.open(full_jar_path)

        def run(self):
            self.download_app = appuifw.Listbox(self.links_names, self.handler)
            return self.download_app
    
    def handle_tab(self, index):
        if index == 0:
            self.title = 'Info | %s' % self.app_title
            self.body = self.app_simple_info()
        elif index == 1:
            self.title = 'Screenshots | %s' % self.app_title
            self.body = self.AppScreenshots(self).run()
        elif index == 2:
            self.title = 'Description | %s' % self.app_title
            self.body = self.app_description()
        elif index == 3:
            self.title = 'Links | %s' % self.app_title
            self.body = self.Download(self.download_links, self).run()

def close_all_views():
    while appuifw.app.view:
        appuifw.app.view.close()

class OpenByLink:
    def __init__(self):
        pass

    def run(self):
        link = appuifw.query(u"Input Dedomil Game link", "text")
        if not link:
            return
        close_all_views()
        if not "dedomil.net/games" in link:
            appuifw.note(u"Not a Dedomil link", "error")
            return
        try:
            game_resolutions = api.get_resolutions(link)
        except urllib.URLError:
            appuifw.note(u"Failed fetching info", "error")
            return

        if not len(game_resolutions) > 0:
            appuifw.note(u"No resolutions available...")
            return

        resolutions_names = []
        resolutions_links = []
        for key, value in game_resolutions.items():
            resolutions_names.append(key)
            resolutions_links.append(value)
        if device_res in resolutions_names:
            gameinfo = api.get_app_info(resolutions_links[resolutions_names.index(device_res)])
            game_description_view = GameDescriptionView(gameinfo)
            appuifw.app.view = game_description_view
        else:
            game_resolutions_view = self.GameResolutionsView(resolutions_names, resolutions_links)
            appuifw.app.view = game_resolutions_view

    class GameResolutionsView(appuifw.View):
        def __init__(self, resolutions_names, resolutions_links):
            appuifw.View.__init__(self)

            self.resolutions_names = resolutions_names
            self.resolutions_links = resolutions_links

            # View Properties
            self.exit_key_text = u'Back'
            self.menu = default_menu
            self.title = u'Resolutions'
            self.body = self.run()
            # End of View Properties

        def handler(self):
            index = self.resolutions_app.current()
            gameinfo = api.get_app_info(self.resolutions_links[index])
            game_description_view = GameDescriptionView(gameinfo)
            appuifw.app.view = game_description_view

        def run(self):
            self.resolutions_app = appuifw.Listbox(self.resolutions_names, self.handler)
            return self.resolutions_app
        
class App1:
    def __init__(self):
        self.entries_links = [
            "http://dedomil.net/games/search",
            "http://dedomil.net/games/vendors/page/1",
            "http://dedomil.net/games/screens",
            "http://dedomil.net/games/category/1"
        ]

        self.entries = [
            u"Search", u"Vendors", u"Resolutions", u"Nokia Games"
        ]

    def handler(self):
        index = self.app1.current()
        appuifw.app.set_tabs([u"Functions", u"About"], handle_tab)
        if index == 0:
            query = appuifw.query(u"Query to search:", "text")
            if not query:
                return

            if not len(query) > 3:
                appuifw.note(u"Query should be 3-digits or longer", "error")
                return
            search_results_view = self.SearchResultsView(query)
            if not search_results_view.results:
                return
            appuifw.app.view = search_results_view

        elif index == 1:
            vendors_view = self.VendorsView(self.entries_links[index])
            appuifw.app.view = vendors_view
        elif index == 2:
            resolutions_view = self.Resolutions(self.entries_links[index])
            appuifw.app.view = resolutions_view
        elif index == 3:
            nokia_games_view = self.NokiaGames(self.entries_links[index])
            if nokia_games_view.skip_res:
                return
            else:
                appuifw.app.view = nokia_games_view

    def run(self):
        self.app1 = appuifw.Listbox(self.entries, self.handler)
        return self.app1

    class SearchResultsView(appuifw.View):
        def __init__(self, query):
            appuifw.View.__init__(self)

            self.results = True
            self.page = 1 # Default

            response = api.search(query, self.page)
            
            if not len(response.get("results")) > 0:
                appuifw.note(u"No results!")
                self.results = False
                return
            
            self.page = self.page
            self.total_pages = response["total_pages"]
            
            self.results_names = []
            self.results_ids = []

            for result in response["results"]:
                self.results_names.append(result["title"])
                self.results_ids.append(result['id'])

            self.query = query
            
            # View Properties
            self.exit_key_text = u"Back"

            if self.total_pages > 0:
                self.pages = True
            else:
                self.pages = False

            if self.pages:
                self.menu = [
                    (u"Next page", self.fetch_next_page),
                    (u"Last page", self.fetch_last_page)] + default_menu
                self.title = u"Search results | %d" % self.page
            else:
                self.menu = default_menu
                self.title = u'Search results'
            self.body = self.run()
            # End of View Properties

        def fetch_page(self, action):
            if action == "next":
                page = self.page + 1
            elif action == "previous":
                page = self.page - 1
            elif action == "first":
                page = 1
            elif action == "last":
                page = self.total_pages

            self.previous_page = self.page - 1

            response = api.search(self.query, page)
            
            self.results_names = []
            self.results_ids = []

            for result in response["results"]:
                self.results_names.append(result["title"])
                self.results_ids.append(result['id'])

            # View Properties
            if self.pages:
                if self.page != self.total_pages and self.page != 1:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"Search results | %d" % self.page
                elif self.page == 1:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"Search results | %d" % self.page
                elif self.page == self.total_pages:
                    self.menu = [
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page)
                    ] + default_menu
                    self.title = u"Search results | %d" % self.page
            else:
                self.menu = default_menu
                self.title = u'Search results'
            self.body = self.run()
            # End of View Properties

        def fetch_next_page(self):
            self.fetch_page(action="next")

        def fetch_previous_page(self):
            self.fetch_page(action="previous")

        def fetch_first_page(self):
            self.fetch_page(action="first")

        def fetch_last_page(self):
            self.fetch_page(action="last")

        def handler(self):
            index = self.results_app.current()

            game_resolutions = api.get_resolutions(self.results_ids[index])

            if not len(game_resolutions["resolutions"]) > 0:
                appuifw.note(u"No resolutions available...")
                return

            resolutions_names = []

            for key, value in game_resolutions.items():
                resolutions_names.append(key)
            if device_res in resolutions_names:
                gameinfo = api.get_app_info(resolutions_links[resolutions_names.index(device_res)])
                game_description_view = GameDescriptionView(gameinfo)
                appuifw.app.view = game_description_view
            else:
                game_resolutions_view = self.GameResolutionsView(resolutions_names, resolutions_links)
                appuifw.app.view = game_resolutions_view

        def run(self):
            self.results_app = appuifw.Listbox(self.results_names, self.handler)
            return self.results_app

        class GameResolutionsView(appuifw.View):
            def __init__(self, resolutions_names, resolutions_links):
                appuifw.View.__init__(self)

                self.resolutions_names = resolutions_names
                self.resolutions_links = resolutions_links

                # View Properties
                self.exit_key_text = u'Back'
                self.menu = default_menu
                self.title = u'Resolutions'
                self.body = self.run()
                # End of View Properties

            def handler(self):
                index = self.resolutions_app.current()
                gameinfo = api.get_app_info(self.resolutions_links[index])
                game_description_view = GameDescriptionView(gameinfo)
                appuifw.app.view = game_description_view

            def run(self):
                self.resolutions_app = appuifw.Listbox(self.resolutions_names, self.handler)
                return self.resolutions_app
    
    class VendorsView(appuifw.View):
        def __init__(self, link):
            appuifw.View.__init__(self)

            vendors_list = api.retrieve_games(link)
            vendors_names = []
            vendors_links = []

            for key, value in vendors_list.get("results").items():
                vendors_names.append(key)
                vendors_links.append(value.get("link"))
            
            self.vendors_names = vendors_names
            self.vendors_links = vendors_links

            # View Properties
            self.exit_key_text = u"Back"

            if vendors_list.get("current_page") and vendors_list.get("next_page") and vendors_list.get("last_page"):
                self.current_page = vendors_list["current_page"]
                self.first_page = vendors_list["current_page"]
                self.next_page = vendors_list["next_page"]
                self.last_page = vendors_list["last_page"]
                pages = True
            elif vendors_list.get("current_page") and vendors_list.get("last_page"):
                self.current_page = vendors_list["current_page"]
                self.last_page = vendors_list["last_page"]
                pages = True
            else:
                pages = False

            if pages:
                self.menu = [
                    (u"Next page", self.fetch_next_page),
                    (u"Last page", self.fetch_last_page)
                ] + default_menu
                self.title = u"Vendors | %d" % self.current_page[0]
            else:
                self.menu = [(u"Open by link", open_by_link.run)] + default_menu
                self.title = u'Vendors'
            self.body = self.run()
            # End of View Properties
        
        def fetch_page(self, action):
            
            if action == "next":
                link = self.next_page[1]
            elif action == "previous":
                link = self.previous_page[1]
            elif action == "first":
                link = self.first_page[1]
            elif action == "last":
                link = self.last_page[1]
            
            if action in ["next", "last", "previous"]:
                pattern = re.search(r"/page/(\d+)/?", link)
                previous_page_i = int(pattern.group(1)) - 1
                previous_link = re.sub(pattern.group(0), '/page/%d' % previous_page_i, link)
                self.previous_page = [previous_page_i, previous_link]

            vendors_list = api.retrieve_games(link)
            vendors_names = []
            vendors_links = []

            for key, value in vendors_list.get("results").items():
                vendors_names.append(key)
                vendors_links.append(value.get("link"))
            
            self.vendors_names = vendors_names
            self.vendors_links = vendors_links

            if vendors_list.get("current_page") and vendors_list.get("next_page"):
                self.current_page = vendors_list["current_page"]
                self.next_page = vendors_list["next_page"]
                pages = True
            elif vendors_list.get("current_page"):
                self.current_page = vendors_list["current_page"]
                pages = True
            else:
                pages = False

            # View Properties
            if pages and self.current_page[0] != self.last_page[0] and self.current_page[0] != self.first_page[0]:
                self.menu = [
                    (u"Next page", self.fetch_next_page),
                    (u"First page", self.fetch_first_page),
                    (u"Previous page", self.fetch_previous_page),
                    (u"Last page", self.fetch_last_page)
                ] + default_menu
                self.title = u"Vendors | %d" % self.current_page[0]
            elif pages and self.current_page[0] == self.first_page[0]:
                self.menu = [(u"Next page", self.fetch_next_page), (u"Last page", self.fetch_last_page)] + default_menu
                self.title = u"Vendors | %d" % self.current_page[0]
            elif pages and self.current_page[0] == self.last_page[0]:
                self.menu = [
                    (u"First page", self.fetch_first_page),
                    (u"Previous page", self.fetch_previous_page)
                ] + default_menu
                self.title = u"Vendors | %d" % self.current_page[0]
            else:
                self.menu = default_menu
                self.title = u'Vendors'
            self.body = self.run()
            # End of View Properties

        def fetch_next_page(self):
            self.fetch_page(action="next")

        def fetch_previous_page(self):
            self.fetch_page(action="previous")

        def fetch_first_page(self):
            self.fetch_page(action="first")

        def fetch_last_page(self):
            self.fetch_page(action="last")

        def handler(self):
            index = self.vendors_app.current()
            link = self.vendors_links[index]

            self.vendor_title = self.vendors_names[index]
            vendor_view = self.VendorView(link, self)
            appuifw.app.view = vendor_view

        def run(self):
            self.vendors_app = appuifw.Listbox(self.vendors_names, self.handler)
            return self.vendors_app

        class VendorView(appuifw.View):
            def __init__(self, link, vendors_ref):
                appuifw.View.__init__(self)

                self.vendors_ref = vendors_ref
                self.vendors_app = vendors_ref.vendors_app
                games_list = api.retrieve_games(link)
                self.games_list = games_list

                games_names = []
                games_links = []

                for key, value in games_list.get("results").items():
                    games_names.append(key)
                    games_links.append(value.get("link"))

                self.games_names = games_names
                self.games_links = games_links

                # View Properties
                self.exit_key_text = u"Back"

                if games_list.get("current_page") and games_list.get("next_page") and games_list.get("last_page"):
                    self.current_page = games_list["current_page"]
                    self.first_page = games_list["current_page"]
                    self.next_page = games_list["next_page"]
                    self.last_page = games_list["last_page"]
                    pages = True
                elif games_list.get("current_page") and games_list.get("last_page"):
                    self.current_page = games_list["current_page"]
                    self.last_page = games_list["last_page"]
                    pages = True
                else:
                    pages = False

                if pages:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (vendors_ref.vendor_title, self.current_page[0])
                else:
                    self.menu = default_menu
                    self.title = u'%s' % vendors_ref.vendor_title
                self.body = self.run()
                # End of View Properties

            def fetch_page(self, action):
            
                if action == "next":
                    link = self.next_page[1]
                elif action == "previous":
                    link = self.previous_page[1]
                elif action == "first":
                    link = self.first_page[1]
                elif action == "last":
                    link = self.last_page[1]
            
                if action in ["next", "last", "previous"]:
                    pattern = re.search(r"/page/(\d+)/?", link)
                    previous_page_i = int(pattern.group(1)) - 1
                    previous_link = re.sub(pattern.group(0), '/page/%d' % previous_page_i, link)
                    self.previous_page = [previous_page_i, previous_link]

                games_list = api.retrieve_games(link)
                games_names = []
                games_links = []

                for key, value in games_list.get("results").items():
                    games_names.append(key)
                    games_links.append(value.get("link"))

                self.games_names = games_names
                self.games_links = games_links

                if games_list.get("current_page") and games_list.get("next_page"):
                    self.current_page = games_list["current_page"]
                    self.next_page = games_list["next_page"]
                    pages = True
                elif games_list.get("current_page"):
                    self.current_page = games_list["current_page"]
                    pages = True
                else:
                    pages = False

                # View Properties
                if pages and self.current_page[0] != self.last_page[0] and self.current_page[0] != self.first_page[0]:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.vendors_ref.vendor_title, self.current_page[0])
                elif pages and self.current_page[0] == self.first_page[0]:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.vendors_ref.vendor_title, self.current_page[0])
                elif pages and self.current_page[0] == self.last_page[0]:
                    self.menu = [
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.vendors_ref.vendor_title, self.current_page[0])
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.vendors_ref.vendor_title
                self.body = self.run()
                # End of View Properties

            def fetch_next_page(self):
                self.fetch_page(action="next")

            def fetch_previous_page(self):
                self.fetch_page(action="previous")

            def fetch_first_page(self):
                self.fetch_page(action="first")

            def fetch_last_page(self):
                self.fetch_page(action="last")

            def handler(self):
                index = self.vendor_app.current()
                link = self.games_links[index]

                game_resolutions = api.get_resolutions(link)

                if not len(game_resolutions) > 0:
                    appuifw.note(u"No resolutions available...")
                    return

                resolutions_names = []
                resolutions_links = []
                for key, value in game_resolutions.items():
                    resolutions_names.append(key)
                    resolutions_links.append(value)

                if device_res in resolutions_names:
                    gameinfo = api.get_app_info(resolutions_links[resolutions_names.index(device_res)])
                    game_description_view = GameDescriptionView(gameinfo)
                    appuifw.app.view = game_description_view
                else:
                    game_resolutions_view = self.vendors_ref.GameResolutionsView(resolutions_names, resolutions_links)
                    appuifw.app.view = game_resolutions_view

            def run(self):
                self.vendor_app = appuifw.Listbox(self.games_names, self.handler)
                return self.vendor_app

        class GameResolutionsView(appuifw.View):
            def __init__(self, resolutions_names, resolutions_links):
                appuifw.View.__init__(self)

                self.resolutions_names = resolutions_names
                self.resolutions_links = resolutions_links

                # View Properties

                self.exit_key_text = u"Back"
                self.menu = default_menu
                self.title = u'Resolutions'
                self.body = self.run()

                # End of View Properties

            def handler(self):
                index = self.resolutions_app.current()

                gameinfo = api.get_app_info(self.resolutions_links[index])
                game_description_view = GameDescriptionView(gameinfo)
                appuifw.app.view = game_description_view

            def run(self):
                self.resolutions_app = appuifw.Listbox(self.resolutions_names, self.handler)
                return self.resolutions_app

    class Resolutions(appuifw.View):
        def __init__(self, link):
            appuifw.View.__init__(self)

            resolutions_list = api.retrieve_games(link)

            resolutions_names = []
            resolutions_links = []

            for key, value in resolutions_list.get("results").items():
                resolutions_names.append(key)
                resolutions_links.append(value.get("link"))
            
            self.resolutions_names = resolutions_names
            self.resolutions_links = resolutions_links

            # View Properties
            self.title = u"Resolutions"
            self.menu = default_menu
            self.exit_key_text = u"Back"
            self.body = self.run()
            # End of View Properties
        
        def handler(self):
            index = self.resolutions_app.current()
            link = self.resolutions_links[index]
            self.name = self.resolutions_names[index]

            resolution_view = self.ResolutionView(self.name, link, self)
            appuifw.app.view = resolution_view

        def run(self):
            self.resolutions_app = appuifw.Listbox(self.resolutions_names, self.handler)
            return self.resolutions_app

        class ResolutionView(appuifw.View):
            def __init__(self, name, link, resolutions_ref):
                appuifw.View.__init__(self)

                self.name = name
                self.resolutions_ref = resolutions_ref
                self.resolutions_app = resolutions_ref.resolutions_app
                games_list = api.retrieve_games(link)
                self.games_list = games_list

                games_names = []
                games_links = []

                for key, value in games_list.get("results").items():
                    games_names.append(key)
                    games_links.append(value.get("link"))

                self.games_names = games_names
                self.games_links = games_links

                # View Properties
                self.exit_key_text = u"Back"

                if games_list.get("current_page") and games_list.get("next_page") and games_list.get("last_page"):
                    self.current_page = games_list["current_page"]
                    self.first_page = games_list["current_page"]
                    self.next_page = games_list["next_page"]
                    self.last_page = games_list["last_page"]
                    pages = True
                elif games_list.get("current_page") and games_list.get("last_page"):
                    self.current_page = games_list["current_page"]
                    self.last_page = games_list["last_page"]
                    pages = True
                else:
                    pages = False

                if pages:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.name
                self.body = self.run()
                # End of View Properties

            def fetch_page(self, action):
                if action == "next":
                    link = self.next_page[1]
                elif action == "previous":
                    link = self.previous_page[1]
                elif action == "first":
                    link = self.first_page[1]
                elif action == "last":
                    link = self.last_page[1]

                if action in ["next", "last", "previous"]:
                    pattern = re.search(r"/page/(\d+)/?", link)
                    previous_page_i = int(pattern.group(1)) - 1
                    previous_link = re.sub(pattern.group(0), '/page/%d' % previous_page_i, link)
                    self.previous_page = [previous_page_i, previous_link]

                games_list = api.retrieve_games(link)
                self.games_list = games_list

                games_names = []
                games_links = []

                for key, value in games_list.get("results").items():
                    games_names.append(key)
                    games_links.append(value.get("link"))

                self.games_names = games_names
                self.games_links = games_links

                if games_list.get("current_page") and games_list.get("next_page"):
                    self.current_page = games_list["current_page"]
                    self.next_page = games_list["next_page"]
                    pages = True
                elif games_list.get("current_page"):
                    self.current_page = games_list["current_page"]
                    pages = True
                else:
                    pages = False

                # View Properties
                if pages and self.current_page[0] != self.last_page[0] and self.current_page[0] != self.first_page[0]:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                elif pages and self.current_page[0] == self.first_page[0]:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                elif pages and self.current_page[0] == self.last_page[0]:
                    self.menu = [
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.name
                self.body = self.run()
                # End of View Properties

            def fetch_next_page(self):
                self.fetch_page(action="next")

            def fetch_previous_page(self):
                self.fetch_page(action="previous")

            def fetch_first_page(self):
                self.fetch_page(action="first")

            def fetch_last_page(self):
                self.fetch_page(action="last")

            def handler(self):
                index = self.resolution_app.current()
                link = self.games_links[index]

                gameinfo = api.get_app_info(link)
                game_description_view = GameDescriptionView(gameinfo)
                appuifw.app.view = game_description_view

            def run(self):
                self.resolution_app = appuifw.Listbox(self.games_names, self.handler)
                return self.resolution_app

    class NokiaGames(appuifw.View):
        def __init__(self, link):
            appuifw.View.__init__(self)

            resolutions_list = api.retrieve_games(link)
            resolutions_names = []
            resolutions_links = []

            for key, value in resolutions_list.get("results").items():
                resolutions_names.append(key)
                resolutions_links.append(value.get("link"))
            if u"All resolutions" in resolutions_names:
                _current_index = resolutions_names.index(u"All resolutions")
                _all_res_link = resolutions_links[_current_index]
                _new_index = 0
                resolutions_names.pop(_current_index)
                resolutions_links.pop(_current_index)
                resolutions_names.insert(_new_index, u"All resolutions")
                resolutions_links.insert(_new_index, _all_res_link)
            
            self.resolutions_names = resolutions_names
            self.resolutions_links = resolutions_links

            self.skip_res = False
            if device_res in resolutions_names:
                link = resolutions_links[resolutions_names.index(device_res)]
                resolution_view = self.ResolutionView(device_res, link)
                self.skip_res = True
                appuifw.app.view = resolution_view
            else:
                # View Properties
                self.title = u"Nokia Games"
                self.menu = default_menu
                self.exit_key_text = u"Back"
                self.body = self.run()
                # End of View Properties
        
        def handler(self):
            index = self.resolutions_app.current()
            link = self.resolutions_links[index]
            self.name = self.resolutions_names[index]

            resolution_view = self.ResolutionView(self.name, link)
            appuifw.app.view = resolution_view

        def run(self):
            self.resolutions_app = appuifw.Listbox(self.resolutions_names, self.handler)
            return self.resolutions_app

        class ResolutionView(appuifw.View):
            def __init__(self, name, link):
                appuifw.View.__init__(self)

                self.name = name
                games_list = api.retrieve_games(link)
                self.games_list = games_list

                games_names = []
                games_links = []

                for key, value in games_list.get("results").items():
                    games_names.append(key)
                    games_links.append(value.get("link"))

                self.games_names = games_names
                self.games_links = games_links

                # View Properties
                self.exit_key_text = u"Back"

                if games_list.get("current_page") and games_list.get("next_page") and games_list.get("last_page"):
                    self.current_page = games_list["current_page"]
                    self.first_page = games_list["current_page"]
                    self.next_page = games_list["next_page"]
                    self.last_page = games_list["last_page"]
                    pages = True
                elif games_list.get("current_page") and games_list.get("last_page"):
                    self.current_page = games_list["current_page"]
                    self.last_page = games_list["last_page"]
                    pages = True
                else:
                    pages = False

                if pages:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.name
                self.body = self.run()
                # End of View Properties

            def fetch_page(self, action):
                if action == "next":
                    link = self.next_page[1]
                elif action == "previous":
                    link = self.previous_page[1]
                elif action == "first":
                    link = self.first_page[1]
                elif action == "last":
                    link = self.last_page[1]

                if action in ["next", "last", "previous"]:
                    pattern = re.search(r"/page/(\d+)/?", link)
                    previous_page_i = int(pattern.group(1)) - 1
                    previous_link = re.sub(pattern.group(0), '/page/%d' % previous_page_i, link)
                    self.previous_page = [previous_page_i, previous_link]

                games_list = api.retrieve_games(link)
                self.games_list = games_list

                games_names = []
                games_links = []

                for key, value in games_list.get("results").items():
                    games_names.append(key)
                    games_links.append(value.get("link"))

                self.games_names = games_names
                self.games_links = games_links

                if games_list.get("current_page") and games_list.get("next_page"):
                    self.current_page = games_list["current_page"]
                    self.next_page = games_list["next_page"]
                    pages = True
                elif games_list.get("current_page"):
                    self.current_page = games_list["current_page"]
                    pages = True
                else:
                    pages = False

                # View Properties
                if pages and self.current_page[0] != self.last_page[0] and self.current_page[0] != self.first_page[0]:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                elif pages and self.current_page[0] == self.first_page[0]:
                    self.menu = [
                        (u"Next page", self.fetch_next_page),
                        (u"Last page", self.fetch_last_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                elif pages and self.current_page[0] == self.last_page[0]:
                    self.menu = [
                        (u"First page", self.fetch_first_page),
                        (u"Previous page", self.fetch_previous_page)
                    ] + default_menu
                    self.title = u"%s | %d" % (self.name, self.current_page[0])
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.name
                self.body = self.run()
                # End of View Properties

            def fetch_next_page(self):
                self.fetch_page(action="next")

            def fetch_previous_page(self):
                self.fetch_page(action="previous")

            def fetch_first_page(self):
                self.fetch_page(action="first")

            def fetch_last_page(self):
                self.fetch_page(action="last")

            def handler(self):
                index = self.resolution_app.current()
                link = self.games_links[index]

                gameinfo = api.get_app_info(link)
                game_description_view = GameDescriptionView(gameinfo)
                appuifw.app.view = game_description_view

            def run(self):
                self.resolution_app = appuifw.Listbox(self.games_names, self.handler)
                return self.resolution_app

class App2:
    def __init__(self):
        pass

    def run(self):
        about = appuifw.Text(scrollbar=True, skinned=True)
        about.font = (u"Nokia Sans S60", 25)
        about.style = appuifw.STYLE_BOLD
        about.add(u"DedoSurf")
        about.font = (u"Nokia Sans S60", 15)
        about.add(u"\nBy Wunder Wungiel")
        about.add(u"\n\nDedomil.net client for Symbian devices, written in PyS60 1.4.5.")
        about.add(u"\n\n----------------------------\n\n")
        about.add(u"Join our Telegram group:")
        about.style = appuifw.STYLE_UNDERLINE
        about.add(u"\n\nhttps://t.me/symbian_world")
        return about

    def run_body(self):  # Automatic version
        close_all_views()
        about_app = self.run()
        appuifw.app.activate_tab(1)
        appuifw.app.title = u"About"
        appuifw.app.body = about_app

app1 = App1()
app2 = App2()
open_by_link = OpenByLink()

def handle_tab(index):
    appuifw.app.exit_key_handler = exit_key_handler
    if index == 0:
        appuifw.app.title = u"DedoSurf"
        appuifw.app.body = app1.run()
    if index == 1:
        appuifw.app.title = u"About"
        appuifw.app.body = app2.run()
    
def exit_key_handler():
    app_lock.signal()  # Action to do when user presses exit on first view (functions / about)
    appuifw.app.set_exit()

app_lock = e32.Ao_lock()
file_opener = appuifw.Content_handler()  # Defines an instance of Content_handler for opening files directly
default_menu = [(u"Open by link", open_by_link.run), (u"About", app2.run_body), (u"Exit", exit_key_handler)]
appuifw.app.menu = default_menu
appuifw.app.set_tabs([u"Functions", u"About"], handle_tab)
appuifw.app.title = u'DedoSurf'
appuifw.app.screen = "normal"
appuifw.app.body = app1.run()
appuifw.app.exit_key_handler = exit_key_handler
app_lock.wait()
