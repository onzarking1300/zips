import requests,json,xbmc,xbmcplugin,xbmcaddon,xbmcgui,sys,urllib.parse

addon=xbmcaddon.Addon()
addon_name=addon.getAddonInfo('name')
addon_icon=addon.getAddonInfo('icon')
addon_fanart=addon.getAddonInfo('fanart')
addon_handle=int(sys.argv[1])
sess = requests.Session()

base_url='https://gdltv.live'

def addLink(name,url,icon=addon_icon,fanart=addon_fanart,isFolder=False):
    u = '%s?action=%s' % (sys.argv[0], url)
    li = xbmcgui.ListItem(label=name)
    li.setArt({'icon': icon, 'fanart': fanart})
    if isFolder is False: li.setProperty('isPlayable', 'true')
    xbmcplugin.addDirectoryItem(addon_handle,u,listitem=li,isFolder=isFolder)

def play_video():

    title = params.get('title')
    image = params.get('image_url')

    playurl = url.split('?')[0]

    li=xbmcgui.ListItem(label=title,path=playurl,offscreen=True)
    li.setArt({'icon': image})
    li.setInfo('video', {title: 'title'})

    xbmcplugin.setResolvedUrl(addon_handle,True,listitem=li)


def get_channels():
    loaded=0
    chns=[]
    dialog=xbmcgui.DialogProgress()
    dialog.create(addon_name, 'Creating channel listing....')
    channelgenre=urllib.parse.unquote_plus(genre).strip()
    for i in range(totalpages): 
        r=sess.get(f'{base_url}/channels_{i}.json')
        if r:
            text=r.text
            ch=json.loads(text)
            current_page = i + 1
            percent=int((current_page/totalpages)*100)
            dialog.update(percent,f'{i} out of {totalpages} pages loaded...')
            for x in ch:
                try:
                    n=''
                    l=''
                    u=''
                    g=''
                    g=x.get('g','')
                    if g.lower().strip() == channelgenre.lower():
                        n=x.get('n')
                        l=x.get('l',addon_icon)
                        u=x.get('u')
                        add={'title':n,'image':l,'genre':g,'url':u}
                        chns.append(add)
                    else:
                        raise Exception
                except:
                    pass
    dialog.close()
    for chn in chns:
        xbmcplugin.setPluginCategory(addon_handle, addon_name)
        xbmcplugin.setContent(addon_handle, addon_name)
        title = chn['title']
        url = chn['url']
        image = chn['image']
        addLink(title,f'play&url={url}&genre={genre}&title={urllib.parse.quote_plus(title)}&image_url={image}',image,isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)


def main():
    xbmcplugin.setPluginCategory(addon_handle,'')
    xbmcplugin.setContent(addon_handle,'')
    url='https://gdltv.live/channels_index.json'
    r=sess.get(url).json()
    if r:
        totalPages=int(r['pages'])
        for i in r['groups']:
            addLink(i, f'get_channels&genre={urllib.parse.quote_plus(i)}&totalpages={totalPages}',addon_icon,isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)


try:
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
except:
    params = []
try:
    url = params.get('url')
except:
    url = None
try:
    action = params.get('action')
except:
    action = None
try:
    genre = params.get('genre')
except:
    genre = None
try:
    totalpages = int(params.get('totalpages'))
except:
    totalpages = None

xbmc.log(f'{params}',xbmc.LOGINFO)

if not params:
    main()
elif action == 'get_channels':
    get_channels()
elif action == 'play':
    play_video()