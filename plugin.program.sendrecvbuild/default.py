import urllib.request
import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs
import sys, urllib.parse, threading, shutil, os, zipfile
from http.server import SimpleHTTPRequestHandler
import socket, socketserver 

addon=xbmcaddon.Addon()
addon_path=addon.getAddonInfo('path')
addon_icon=addon.getAddonInfo('icon')
addon_id=addon.getAddonInfo('id')
addon_name=addon.getAddonInfo('name')

PORT=4278
httpd_server=None
server_thread=None
home = xbmcvfs.translatePath('special://home')
export = xbmcvfs.translatePath('special://temp')
keep_userdata = True

def log(text,lvl=xbmc.LOGINFO):
    if isinstance(text, str):
        text=str(text)
                      
    xbmc.log(f'[{addon_id}] {text}',level=lvl)

def addLink(name, url, desc='', icon='DefaultFolder.png', fanart='', isFolder=True):
    u = sys.argv[0] + '?action=%s' % url
    li = xbmcgui.ListItem(label=name)
    li.setArt({'thumb':icon, 'icon': icon, 'fanart': fanart})
    li.setInfo('video', infoLabels={'plot': desc})
    if not isFolder:
        li.setProperty('isPlayable', 'true')
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), u, listitem=li, isFolder=isFolder)

def force_close():
    os._exit(0)

def get_platform():
    if xbmc.getCondVisibility('System.Platform.Windows'):
        platform = 'windows'
    elif xbmc.getCondVisibility('System.Platform.Linux'): # and Raspberry PI (OSMC/LibreELEC)
        platform = 'linux'
    elif xbmc.getCondVisibility('System.Platform.Android'):
        platform = 'android'
    elif xbmc.getCondVisibility('System.Platform.OSX'):
        platform = 'osx'
    elif xbmc.getCondVisibility('System.Platform.IOS'):
        platform = 'ios'
    else:
        platform = 'unknown'
    return platform

def get_ip_address():
    import socket
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80))
        ip=s.getsockname()[0]
    except:
        hostname=socket.gethostname()
        ip=socket.gethostbyname(hostname)
    return ip

def get_size_of_drive():
    try:
        total, used, free = shutil.disk_usage(xbmcvfs.translatePath('special://home'))
        total = round(total/(1024**3),2)
        used = round(used/(1024**3),2)
        free = round(free/(1024**3),2)
        return (total,used,free)
    except Exception:
        log('Error getting size of Kodi path')
        return ('Unknown', 'Unknown', 'Unknown')

def get_info():
    
    platform = get_platform()
    kodi_version = xbmc.getInfoLabel('System.BuildVersion').split(' ')[0]
    ip_address = get_ip_address()
    total, used, free = get_size_of_drive()


    xbmcgui.Dialog().textviewer(f'{addon_name} - Information about device',
                                f'Running version: {kodi_version}\n'
                                f'Platform: {platform.title()}\n'
                                f'IP Address: {ip_address}  PORT: {PORT}\n'
                                f'Used Space: {used} GB\nFree Space: {free} GB\nTotal Space: {total} GB\n')

def delete_everything():
    global keep_userdata
    whitelist = [addon_id,'EXPORT.zip']
    if keep_userdata == True:
        whitelist.append('userdata')
    for root,dirs,files in os.walk(home):
        for file in files:
            path = os.path.join(root, file)
            for i in whitelist:
                if i in path or 'EXPORT.zip' in path:
                    continue
                try:
                    os.remove(path)
                except:
                    continue
    for root,dirs,files in os.walk(home,topdown=False):
        for i in whitelist:
            if i in path or 'EXPORT.zip' in path:
                    continue
            try:
                if not os.listdir(root) and root != home:
                    os.rmdir(root)
            except:
                continue


def run_http_server():
    global httpd_server
    try:
        if not os.path.exists(export): 
            os.makedirs(export)
        os.chdir(export)

        class http_server(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True

        handler = SimpleHTTPRequestHandler

        httpd_server = http_server(("", PORT), handler)

        log(f'HTTP server listening on port {PORT}, serving from {export}')

        httpd_server.serve_forever()
    except Exception as e:
        log(f'running http server error: {e}')
        return

def stop_http_server():
    global httpd_server,server_thread
    if httpd_server is not None:
        httpd_server.shutdown()
        httpd_server.server_close()
        http_server=None

def view_kodi_log():
    kodi_log_path=os.path.join(xbmcvfs.translatePath('special://logpath'), 'kodi.log')
    with open(kodi_log_path, 'r') as f:
        xbmcgui.Dialog().textviewer(f'{addon_name} - kodi.log', f.read())

def clear_kodi_log():
    try:
        kodi_log_path=os.path.join(xbmcvfs.translatePath('special://logpath'), 'kodi.log')
        with open(kodi_log_path, 'w') as f:
            f.write(' ')
        xbmcgui.Dialog().notification(addon_name, 'Kodi log cleared!')
    except:
        xbmcgui.Dialog().notification(addon_name, 'Failed to clear kodi log.')
        return

def send():

    ip_address = get_ip_address()
    global httpd_server
    if httpd_server is not None:
        xbmcgui.Dialog().notification(addon_name, 'Server is already running')
        return
    dialog = xbmcgui.DialogProgress()
    dialog.create(addon_name, ' Packing your Kodi configuation....\n\nThis may take a minute depending on your build size')
    zip_export_path = os.path.join(export, 'EXPORT.zip')
    try:
        if os.path.exists(zip_export_path):
            os.remove(zip_export_path)
        dialog.update(50,'Compressing...this may take a while!\n\nKeep your device on!')

        total_files = 0
        for root,dirs,files in os.walk(home):
            for file in files:
                if os.path.join(root,file)!=zip_export_path:
                    total_files+=1

        zipped_files=0
        with zipfile.ZipFile(zip_export_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root,dirs,files in os.walk(home):
                for file in files:
                    cur_filepath = os.path.join(root,file)
                    if cur_filepath == zip_export_path:
                        continue
                    relpath = os.path.relpath(cur_filepath, home)
                    try:
                        zf.write(cur_filepath, relpath)
                        zipped_files+=1
                    except Exception:
                        continue
                    finally:
                        zipped_files+=1
                    if dialog.iscanceled():
                        dialog.close()
                        xbmcgui.Dialog().ok(addon_name, 'Compression aborted by user.')
                        return
                    percent = int((zipped_files / total_files) * 100)
                    dialog.update(percent, f'Compressing: {percent}% complete')
        dialog.close()
    except Exception as e:
        dialog.close()
        log(f'Error: {e}')
        xbmcgui.Dialog().notification(addon_name, f'Could not compress build: {str(e)}')
    server_thread = threading.Thread(target=run_http_server)
    server_thread.start()
    dl_url = f'http://{ip_address}:{PORT}'

    info_msg = (
        'The server is broadcasting!\n\n'
        f'Target URL:\n\n[B]{dl_url}[/B]\n\n'
        'Leave this dialog OPEN until the receiving device finishes downloading.\n'
        'Closing this dialog will turn off the server.\n')
    xbmcgui.Dialog().ok(addon_name, info_msg)
    xbmcgui.Dialog().notification(addon_name, 'Shutting down server')

    stop_http_server()
    
    if os.path.exists(zip_export_path):
        os.remove(zip_export_path)

    


def receive():

    zip_export_path = os.path.join(export, 'EXPORT.zip')

    #enter sender ip address
    dialog2 = xbmcgui.DialogProgress()
    keyboard = xbmc.Keyboard('192.168.1.', 'Enter Sender IP Address')
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return
    sender_ip = keyboard.getText().strip()
    dl_url = f'http://{sender_ip}:{PORT}/EXPORT.zip'
    dialog2.create(addon_name, 'Checking build size...')
    
    #hook
    def dl_hook(cnt,block_size,total_size):
        if dialog2.iscanceled():
            raise Exception('Download aborted by user.')
        
        percent=int(cnt*block_size*100/total_size)
        downloaded=round((cnt*block_size)/(1024*1024),1)
        total=round(total_size/(1024*1024),1)
        dialog2.update(percent, f'Downloading: {percent}% ({downloaded} / {total})\n'
                       'Keep both devices on and on the same WI-Fi.')

    try:
        if os.path.exists(zip_export_path):
            os.remove(zip_export_path)
        req=urllib.request.Request(dl_url, method='HEAD')
        with urllib.request.urlopen(req,timeout=10) as resp:
            remote_size = int(resp.headers.get('Content-Length',0))
    except Exception as e:
        dialog2.close()
        xbmcgui.Dialog().ok(addon_name, 'Connection Failed')
        log(f'Error: {e}')
        return

    if remote_size:
        gb = round(remote_size/(1024**3),2)
        needed=round(gb*2.2,2)
        _,used,free=get_size_of_drive()
        if free < needed:
            dialog2.close()
            xbmcgui.Dialog().ok(addon_name, 'Error: Not enough space!')
            return
    else:
        return

    delete_everything()

    urllib.request.urlretrieve(dl_url, zip_export_path, reporthook=dl_hook)

    dialog2.close()

    dialog2.create(addon_name, 'Extracting build...')
    try:
        with zipfile.ZipFile(zip_export_path, 'r') as zf:
            file_list = zf.namelist()
            total_files = len(file_list)
            for idx,file in enumerate(file_list):
                if dialog2.iscanceled():
                    xbmcgui.Dialog().ok(addon_name, 'Installation failed')
                    dialog2.close()
                    return
                try:
                    zf.extract(file,home)
                except:
                    continue
                percent = int((idx / total_files) * 100)
                dialog2.update(percent, f'Writing file {idx} of {total_files}')
        dialog2.close()
    except Exception as e:
        dialog2.close()
        xbmcgui.Dialog().ok(addon_name, 'Extraction Error')
        log(f'Error: {e}')
        return
    finally:
        if os.path.exists(zip_export_path):
            os.remove(zip_export_path)
    xbmcgui.Dialog().ok(addon_name,
                        'Installation complete!\n\n'
                        'Kodi will now force close to save changes.')

    force_close()

def MainMenu():

    addLink('Send build to device','send',isFolder=True)
    addLink('Receive build from device','receive',isFolder=True)
    addLink('Get Information about your device','info_device',isFolder=True)
    addLink('.....................................','',isFolder=True)
    addLink('View kodi log','viewkodilog',isFolder=True)
    addLink('Clear kodi log','clearkodilog',isFolder=True)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


xbmcplugin.setPluginCategory(int(sys.argv[1]), addon_name)
xbmcplugin.setContent(int(sys.argv[1]), addon_name)

params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
action = params.get('action','')

if not params:
    MainMenu()
elif action=='send':
    send()
elif action=='receive':
    receive()
elif action=='info_device':
    get_info()
elif action=='viewkodilog':
    view_kodi_log()
elif action=='clearkodilog':
    clear_kodi_log()