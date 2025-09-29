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

    def resolutions(self, game_id):
        r = urllib.urlopen(self.api_url + "resolutions/?id=%s" % game_id)
        return json.loads(r.read().decode("utf-8"))

    def game(self, game_id, resolution):
        r = urllib.urlopen(self.api_url + "game/?id=%s&resolution=%s" % (game_id, resolution))
        return json.loads(r.read().decode("utf-8"))

    def search(self, query, page):
        r = urllib.urlopen(self.api_url + "search/?q=%s&page=%s" % (query, page))
        return json.loads(r.read().decode("utf-8"))
    
    def vendors(self, page):
        r = urllib.urlopen(self.api_url + "vendors/?page=%s" % page)
        return json.loads(r.read().decode("utf-8"))
    
    def vendor(self, vendor, page):
        vendor = vendor.replace(" ", "%20")
        r = urllib.urlopen(self.api_url + "vendor/?name=%s&page=%s" % (vendor, page))
        return json.loads(r.read().decode("utf-8"))

api = API()

# One liner to grab resolution of device into string in <width>x<height> format
device_resolution = 'x'.join([str(res) for res in sysinfo.display_pixels()])

class GameResolutionsView(appuifw.View):
    def __init__(self, game_id, resolutions):
        appuifw.View.__init__(self)

        self.resolutions = resolutions
        self.game_id = game_id

        # View Properties
        self.exit_key_text = u'Back'
        self.menu = default_menu
        self.title = u'Resolutions'
        self.body = self.run()
        # End of View Properties

    def handler(self):
        index = self.resolutions_app.current()
        game = api.game(self.game_id, self.resolutions[index])
        game_description_view = GameDescriptionView(game)
        appuifw.app.view = game_description_view

    def run(self):
        self.resolutions_app = appuifw.Listbox(self.resolutions, self.handler)
        return self.resolutions_app

class GameDescriptionView(appuifw.View):
    def __init__(self, game):
        appuifw.View.__init__(self)
                
        self.app_title = game["title"]
        self.description = game["description"]
        self.date = game["date"]
        self.downloads = game["downloads"]
        self.download_links = game["resolutions"]
        self.vendor = game["vendor"]
        self.splash = game.get("splash")
        self.screenshot = game.get("screenshot")
                
        # View Properties
        self.exit_key_text = u"Back"
        self.menu = default_menu
        self.set_tabs([u"Info", u"Screenshots", u"Description", u"Links"], self.handle_tab)
        self.title = u'Info | %s' % self.app_title
        self.body = self.game_info()
        # End of View Properties

    def game_info(self):
        info_app = appuifw.Text(scrollbar=True, skinned=True)
        info_app.font = (u"Nokia Sans S60", 25)
        info_app.style = appuifw.STYLE_BOLD
        info_app.add(self.app_title)
        info_app.font = (u"Nokia Sans S60", 15)
        info_app.add("\n\nAdded: %s" % self.date)
        info_app.add("\n\nDownloads: %s" % self.downloads)
        info_app.add("\n\nVendor: %s" % self.vendor)
        return info_app

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
            self.body = self.game_info()
        elif index == 1:
            self.title = 'Screenshots | %s' % self.app_title
            self.body = self.AppScreenshots(self).run()
        elif index == 2:
            self.title = 'Description | %s' % self.app_title
            self.body = self.app_description()
        elif index == 3:
            self.title = 'Links | %s' % self.app_title
            self.body = self.Download(self.download_links, self).run()

class PageChanger:
    def __init__(self, fetch_page):
        self.fetch_page = fetch_page

    def next(self):
        self.fetch_page("next")

    def previous(self):
        self.fetch_page("previous")

    def first(self):
        self.fetch_page("first")

    def last(self):
        self.fetch_page("last")

def close_all_views():
    while appuifw.app.view:
        appuifw.app.view.close()

def generate_menu(title, page, total_pages, fetch_next_page, fetch_first_page, fetch_previous_page, fetch_last_page):

    menu = []
    
    if page != total_pages and page != 1:
        menu = [
            (u"Next page", fetch_next_page),
            (u"First page", fetch_first_page),
            (u"Previous page", fetch_previous_page),
            (u"Last page", fetch_last_page)
        ] + default_menu
        title = u"%s | %d" % (title, page)
    elif page == 1:
        menu = [
            (u"Next page", fetch_next_page),
            (u"Last page", fetch_last_page)
        ] + default_menu
        title = u"%s | %d" % (title, page)
    elif page == total_pages:
        menu = [
            (u"First page", fetch_first_page),
            (u"Previous page", fetch_previous_page)
        ] + default_menu
        title = u"%s | %d" % (title, page)

    return menu, title

class OpenByLink:
    def __init__(self):
        pass

    def run(self):
        link = appuifw.query(u"Input Dedomil Game link", "text")
        if not link:
            return
        
        close_all_views()

        game_id = None
        match = re.search(r"/games/(\d+)/", link)
        if match:
            game_id = match.group(1)

        if not game_id:
            appuifw.note(u"Not a valid link", "error")
            return
        try:
            resolutions = api.resolutions(game_id)
        except urllib.URLError:
            appuifw.note(u"Failed fetching info", "error")
            return

        if not len(resolutions) > 0:
            appuifw.note(u"No resolutions available...")
            return

        if device_resolution in resolutions:
            game = api.game(game_id, device_resolution)
            game_description_view = GameDescriptionView(game)
            appuifw.app.view = game_description_view
        else:
            game_resolutions_view = GameResolutionsView(game_id, resolutions) # We're actually using resolution names as their IDs
            appuifw.app.view = game_resolutions_view
        
class MainTab:
    def __init__(self):
        self.entries = [
            u"Search", u"Vendors", u"Resolutions", u"Nokia Games"
        ]

    def handler(self):
        index = self.main_tab.current()
        appuifw.app.set_tabs([u"Functions", u"About"], handle_tab)
        if index == 0:
            query = appuifw.query(u"Query to search:", "text")
            if not query:
                return

            if not len(query) > 3:
                appuifw.note(u"Query should be 4 characters or longer", "error")
                return
            search_results_view = self.SearchResultsView(query)
            if not search_results_view.results:
                return
            appuifw.app.view = search_results_view

        elif index == 1:
            vendors_view = self.VendorsView()
            appuifw.app.view = vendors_view
        elif index == 2:
            resolutions_view = self.Resolutions()
            appuifw.app.view = resolutions_view
        elif index == 3:
            nokia_games_view = self.NokiaGames()
            if nokia_games_view.skip_res:
                return
            else:
                appuifw.app.view = nokia_games_view

    def run(self):
        self.main_tab = appuifw.Listbox(self.entries, self.handler)
        return self.main_tab

    class SearchResultsView(appuifw.View):
        def __init__(self, query):
            appuifw.View.__init__(self)

            self.page_changer = PageChanger(self.fetch_page)

            self.results = True
            self.query = query
            self.page = 1 # Default

            response = api.search(query, self.page)
            
            if not len(response.get("results")) > 0:
                appuifw.note(u"No results!")
                self.results = False
                return
            
            self.total_pages = response["total_pages"]
            
            self.results_names = []
            self.results_ids = []

            for result in response["results"]:
                self.results_names.append(result["title"])
                self.results_ids.append(result['id'])
            
            # View Properties
            self.exit_key_text = u"Back"

            if self.total_pages > 0:
                self.pages = True
            else:
                self.pages = False

            if self.pages:
                self.menu = [
                    (u"Next page", self.page_changer.next),
                    (u"Last page", self.page_changer.last)] + default_menu
                self.title = u"Search results | %d" % self.page
            else:
                self.menu = default_menu
                self.title = u'Search results'
            self.body = self.run()
            # End of View Properties

        def fetch_page(self, action):

            if action == "next":
                self.page = self.page + 1
            elif action == "previous":
                self.page = self.page - 1
            elif action == "first":
                self.page = 1
            elif action == "last":
                self.page = self.total_pages

            self.previous_page = self.page - 1

            response = api.search(self.query, self.page)
            
            self.results_names = []
            self.results_ids = []

            for result in response["results"]:
                self.results_names.append(result["title"])
                self.results_ids.append(result['id'])

            # View Properties
            if self.pages:
               self.menu, self.title = generate_menu(
                    "Search results",
                    self.page,
                    self.total_pages,
                    self.page_changer.next,
                    self.page_changer.first,
                    self.page_changer.previous,
                    self.page_changer.last
                )
            else:
                self.menu = default_menu
                self.title = u'Search results'
            self.body = self.run()
            # End of View Properties

        def handler(self):
            index = self.results_app.current()

            game_id = self.results_ids[index]
            resolutions = api.resolutions(game_id)

            if not len(resolutions) > 0:
                appuifw.note(u"No resolutions available...")
                return
            
            if device_resolution in resolutions:
                game = api.game(game_id, device_resolution)
                game_description_view = GameDescriptionView(game)
                appuifw.app.view = game_description_view
            else:
                game_resolutions_view = GameResolutionsView(game_id, resolutions) # We're actually using resolution names as their IDs
                appuifw.app.view = game_resolutions_view

        def run(self):
            self.results_app = appuifw.Listbox(self.results_names, self.handler)
            return self.results_app
    
    class VendorsView(appuifw.View):
        def __init__(self):
            appuifw.View.__init__(self)

            self.page_changer = PageChanger(self.fetch_page)

            self.results = True
            self.page = 1 # Default

            response = api.vendors(self.page)
            if not len(response.get("results")) > 0:
                appuifw.note(u"No vendors!")
                self.results = False
                return

            self.vendors = response["results"]
            self.total_pages = response["total_pages"]

            # View Properties
            self.exit_key_text = u"Back"

            if self.total_pages > 0:
                self.pages = True
            else:
                self.pages = False

            if self.pages:
                self.menu = [
                    (u"Next page", self.page_changer.next),
                    (u"Last page", self.page_changer.last)] + default_menu
                self.title = u"Vendors | %d" % self.page
            else:
                self.menu = default_menu
                self.title = u'Vendors'
            self.body = self.run()
            # End of View Properties
        
        def fetch_page(self, action):
            
            if action == "next":
                self.page = self.page + 1
            elif action == "previous":
                self.page = self.page - 1
            elif action == "first":
                self.page = 1
            elif action == "last":
                self.page = self.total_pages
            
            self.vendors = api.vendors(self.page)["results"]

            # View Properties
            if self.pages:
                self.menu, self.title = generate_menu(
                    "Vendors",
                    self.page,
                    self.total_pages,
                    self.page_changer.next,
                    self.page_changer.first,
                    self.page_changer.previous,
                    self.page_changer.last
                )
            else:
                self.menu = default_menu
                self.title = u'Vendors'

            self.body = self.run()
            # End of View Properties

        def handler(self):
            index = self.vendors_app.current()
            vendor = self.vendors[index]

            vendor_view = self.VendorView(vendor)
            appuifw.app.view = vendor_view

        def run(self):
            self.vendors_app = appuifw.Listbox(self.vendors, self.handler)
            return self.vendors_app

        class VendorView(appuifw.View):
            def __init__(self, vendor):
                appuifw.View.__init__(self)

                self.page_changer = PageChanger(self.fetch_page)

                self.results = True
                self.vendor = vendor
                self.page = 1 # Default

                response = api.vendor(self.vendor, self.page)

                self.total_pages = response["total_pages"]
            
                self.results_names = []
                self.results_ids = []

                for result in response["results"]:
                    self.results_names.append(result["title"])
                    self.results_ids.append(result['id'])

                # View Properties
                self.exit_key_text = u"Back"

                if self.total_pages > 0:
                    self.pages = True
                else:
                    self.pages = False

                if self.pages:
                    self.menu = [
                        (u"Next page", self.page_changer.next),
                        (u"Last page", self.page_changer.last)] + default_menu
                    self.title = u"%s | %d" % (vendor, self.page)
                else:
                    self.menu = default_menu
                    self.title = u'%s' % vendor
                self.body = self.run()
                # End of View Properties

            def fetch_page(self, action):
            
                if action == "next":
                    self.page = self.page + 1
                elif action == "previous":
                    self.page = self.page - 1
                elif action == "first":
                    self.page = 1
                elif action == "last":
                    self.page = self.total_pages
        
                response = api.vendor(self.vendor, self.page)

                self.results_names = []
                self.results_ids = []

                for result in response["results"]:
                    self.results_names.append(result["title"])
                    self.results_ids.append(result['id'])

                # View Properties
                if self.pages:
                    self.menu, self.title = generate_menu(
                            self.vendor,
                            self.page,
                            self.total_pages,
                            self.page_changer.next,
                            self.page_changer.first,
                            self.page_changer.previous,
                            self.page_changer.last
                        )
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.vendor
                self.body = self.run()
                # End of View Properties

            def handler(self):
                index = self.vendor_app.current()
                game_id = self.results_ids[index]

                resolutions = api.resolutions(game_id)

                if not len(resolutions) > 0:
                    appuifw.note(u"No resolutions available...")
                    return

                if device_resolution in resolutions:
                    game = api.game(game_id, device_resolution)
                    game_description_view = GameDescriptionView(game)
                    appuifw.app.view = game_description_view
                else:
                    game_resolutions_view = GameResolutionsView(game_id, resolutions) # We're actually using resolution names as their IDs
                    appuifw.app.view = game_resolutions_view

            def run(self):
                self.vendor_app = appuifw.Listbox(self.results_names, self.handler)
                return self.vendor_app

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

                game = api.game(link)
                game_description_view = GameDescriptionView(game)
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
            if device_resolution in resolutions_names:
                link = resolutions_links[resolutions_names.index(device_resolution)]
                resolution_view = self.ResolutionView(device_resolution, link)
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

                game = api.game(link)
                game_description_view = GameDescriptionView(game)
                appuifw.app.view = game_description_view

            def run(self):
                self.resolution_app = appuifw.Listbox(self.games_names, self.handler)
                return self.resolution_app

class AboutTab:
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

main_tab = MainTab()
about_tab = AboutTab()
open_by_link = OpenByLink()

def handle_tab(index):
    appuifw.app.exit_key_handler = exit_key_handler
    if index == 0:
        appuifw.app.title = u"DedoSurf"
        appuifw.app.body = main_tab.run()
    if index == 1:
        appuifw.app.title = u"About"
        appuifw.app.body = about_tab.run()
    
def exit_key_handler():
    app_lock.signal()  # Action to do when user presses exit on first view (functions / about)
    appuifw.app.set_exit()

app_lock = e32.Ao_lock()
file_opener = appuifw.Content_handler()  # Defines an instance of Content_handler for opening files directly
default_menu = [(u"Open by link", open_by_link.run), (u"About", about_tab.run_body), (u"Exit", exit_key_handler)]
appuifw.app.menu = default_menu
appuifw.app.set_tabs([u"Functions", u"About"], handle_tab)
appuifw.app.title = u'DedoSurf'
appuifw.app.screen = "normal"
appuifw.app.body = main_tab.run()
appuifw.app.exit_key_handler = exit_key_handler
app_lock.wait()
