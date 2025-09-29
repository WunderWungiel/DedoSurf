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
host = "http://dedo.wunderwungiel.pl/"

if not os.path.isdir(dl_path):
    os.mkdir(dl_path)
if not os.path.isdir(os.path.join(dl_path, "screenshots")):
    os.mkdir(os.path.join(dl_path, "screenshots"))

class API:
    def __init__(self):
        self.api_url = host + "api/v1/"

    def resolutions(self): # All resolutions of all games
        r = urllib.urlopen(self.api_url + "resolutions/")
        return json.loads(r.read().decode("utf-8"))
    
    def resolution(self, resolution, page): # All games for specific resolution
        r = urllib.urlopen(self.api_url + "resolution/?name=%s&page=%s" % (resolution, page))
        return json.loads(r.read().decode("utf-8"))

    def game_resolutions(self, game_id): # Resolutions for specific game
        r = urllib.urlopen(self.api_url + "game/resolutions/?id=%s" % game_id)
        return json.loads(r.read().decode("utf-8"))

    def game(self, game_id, resolution): # Specific game
        r = urllib.urlopen(self.api_url + "game/?id=%s&resolution=%s" % (game_id, resolution))
        return json.loads(r.read().decode("utf-8"))

    def search(self, query, page):
        query = urllib.quote(query)
        r = urllib.urlopen(self.api_url + "search/?q=%s&page=%s" % (query, page))
        return json.loads(r.read().decode("utf-8"))
    
    def vendors(self, page): # All vendors of all games
        r = urllib.urlopen(self.api_url + "vendors/?page=%s" % page)
        return json.loads(r.read().decode("utf-8"))
    
    def vendor(self, vendor, page): # All games of specific vendor
        vendor = urllib.quote(vendor)
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
        game_view = GameView(game)
        appuifw.app.view = game_view

    def run(self):
        self.resolutions_app = appuifw.Listbox(self.resolutions, self.handler)
        return self.resolutions_app

class GameView(appuifw.View):
    def __init__(self, game):
        appuifw.View.__init__(self)
                
        self.game_title = game["title"]
        self.description = game["description"]
        self.date = game["date"]
        self.downloads = game["downloads"]
        self.models = game["files"]
        self.vendor = game["vendor"]
        self.splash = game.get("splash")
        self.screenshot = game.get("screenshot")
                
        # View Properties
        self.exit_key_text = u"Back"
        self.menu = default_menu
        self.set_tabs([u"Info", u"Screenshots", u"Description", u"Links"], self.handle_tab)
        self.title = u'Info | %s' % self.game_title
        self.body = self.game_info()
        # End of View Properties

    def game_info(self):
        info_app = appuifw.Text(scrollbar=True, skinned=True)
        info_app.font = (u"Nokia Sans S60", 25)
        info_app.style = appuifw.STYLE_BOLD
        info_app.add(self.game_title)
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
        def __init__(self, screenshot):
            self.skip = None

            url = host + "static/images/screenshots/" + screenshot

            if not screenshot:
                self.skip = True
                return
   
            path = os.path.join(dl_path, "screenshots", screenshot)
            if not os.path.isfile(path):
                r = urllib.urlopen(url)
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
        def __init__(self, models, description_ref):
            self.models = models
            self.models_names = []

            for model in self.models.keys():
                model = model.replace(description_ref.game_title, '').strip()
                self.models_names.append(model)

            self.description_ref = description_ref

        def handler(self):
            index = self.download_app.current()
            files = self.models[list(self.models.keys())[index]] # Get the files array from self.models using current index
            filenames = [file['filename'] for file in files]

            choice = appuifw.selection_list(choices=filenames)
            if choice == None:
                return

            self.download(files[choice])
            
        def download(self, file):
            try:
                url = host + "static/files/" + file['filename']
                response = urllib.urlopen(url)
            except urllib.HTTPError:
                appuifw.note(u"Error while downloading game", "error")
                return
            except urllib.URLError:
                appuifw.note(u"Error while downloading game", "error")
                return
            
            path = os.path.join(dl_path, file['filename'])

            appuifw.note(u"Wait... Downloading %s" % file['filename'])
            f = open(path, "wb")
            while True:
                chunk = response.read(1024)
                if not chunk:
                    break
                f.write(chunk)
            f.close()

            nested_path = None
            interrupted = False
            
            if file['type'] == 'download':
                zip_file = zipfile.ZipFile(path, 'r')
                for name in zip_file.namelist():
                    if name.endswith(".jar"):
                        nested_path = os.path.join(dl_path, name)
                        extracted = open(nested_path, "wb")
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
                os.remove(nested_path)
                file_opener.open(path)
            else:
                if nested_path:
                    file_opener.open(nested_path)
                else:
                    file_opener.open(path)

        def run(self):
            self.download_app = appuifw.Listbox(self.models_names, self.handler)
            return self.download_app
    
    def handle_tab(self, index):
        if index == 0:
            self.title = 'Info | %s' % self.game_title
            self.body = self.game_info()
        elif index == 1:
            self.title = 'Screenshots | %s' % self.game_title
            self.body = self.AppScreenshots(self.screenshot).run()
        elif index == 2:
            self.title = 'Description | %s' % self.game_title
            self.body = self.app_description()
        elif index == 3:
            self.title = 'Links | %s' % self.game_title
            self.body = self.Download(self.models, self).run()

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
            resolutions = api.game_resolutions(game_id)
        except urllib.URLError:
            appuifw.note(u"Failed fetching info", "error")
            return

        if not len(resolutions) > 0:
            appuifw.note(u"No resolutions available...")
            return

        if device_resolution in resolutions:
            game = api.game(game_id, device_resolution)
            game_view = GameView(game)
            appuifw.app.view = game_view
        else:
            game_resolutions_view = GameResolutionsView(game_id, resolutions) # We're actually using resolution names as their IDs
            appuifw.app.view = game_resolutions_view
        
class MainTab:
    def __init__(self):
        self.entries = [
            u"Search", u"Vendors", u"Resolutions"
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
            resolutions_view = self.ResolutionsView()
            appuifw.app.view = resolutions_view

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
            resolutions = api.game_resolutions(game_id)

            if not len(resolutions) > 0:
                appuifw.note(u"No resolutions available...")
                return
            
            if device_resolution in resolutions:
                game = api.game(game_id, device_resolution)
                game_view = GameView(game)
                appuifw.app.view = game_view
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

                resolutions = api.game_resolutions(game_id)

                if not len(resolutions) > 0:
                    appuifw.note(u"No resolutions available...")
                    return

                if device_resolution in resolutions:
                    game = api.game(game_id, device_resolution)
                    game_view = GameView(game)
                    appuifw.app.view = game_view
                else:
                    game_resolutions_view = GameResolutionsView(game_id, resolutions) # We're actually using resolution names as their IDs
                    appuifw.app.view = game_resolutions_view

            def run(self):
                self.vendor_app = appuifw.Listbox(self.results_names, self.handler)
                return self.vendor_app

    class ResolutionsView(appuifw.View):
        def __init__(self):
            appuifw.View.__init__(self)

            self.resolutions = api.resolutions()

            # View Properties
            self.title = u"Resolutions"
            self.menu = default_menu
            self.exit_key_text = u"Back"
            self.body = self.run()
            # End of View Properties
        
        def handler(self):
            index = self.resolutions_app.current()
            resolution = self.resolutions[index]

            resolution_view = self.ResolutionView(resolution)
            appuifw.app.view = resolution_view

        def run(self):
            self.resolutions_app = appuifw.Listbox(self.resolutions, self.handler)
            return self.resolutions_app
        
        class ResolutionView(appuifw.View):
            def __init__(self, resolution):
                appuifw.View.__init__(self)
                
                self.page_changer = PageChanger(self.fetch_page)

                self.results = True
                self.resolution = resolution
                self.page = 1 # Default

                response = api.resolution(self.resolution, self.page)
                
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

                self.exit_key_text = u"Back"

                if self.total_pages > 0:
                    self.pages = True
                else:
                    self.pages = False

                if self.pages:
                    self.menu = [
                        (u"Next page", self.page_changer.next),
                        (u"Last page", self.page_changer.last)] + default_menu
                    self.title = u"%s | %d" % (self.resolution, self.page)
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.resolution
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

                response = api.resolution(self.resolution, self.page)

                self.results_names = []
                self.results_ids = []

                for result in response["results"]:
                    self.results_names.append(result["title"])
                    self.results_ids.append(result['id'])

                # View Properties
                if self.pages:
                    self.menu, self.title = generate_menu(
                        self.resolution,
                        self.page,
                        self.total_pages,
                        self.page_changer.next,
                        self.page_changer.first,
                        self.page_changer.previous,
                        self.page_changer.last
                    )
                else:
                    self.menu = default_menu
                    self.title = u'%s' % self.resolution
                self.body = self.run()
                # End of View Properties

            def handler(self):
                index = self.resolution_app.current()
                game_id = self.results_ids[index]

                game = api.game(game_id, self.resolution)
                game_view = GameView(game)
                appuifw.app.view = game_view

            def run(self):
                self.resolution_app = appuifw.Listbox(self.results_names, self.handler)
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
