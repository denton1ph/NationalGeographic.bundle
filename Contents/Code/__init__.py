POD_FEED = "http://feeds.nationalgeographic.com/ng/photography/photo-of-the-day/"
BASE_URL = "http://video.nationalgeographic.com"
JSON_CAT_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/main_sections.json"
JSON_CHANNEL_CAT_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/category_%s.json"
JSON_PLAYLIST_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/lineup_%s_%s.json"
JSON_VIDEO_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/video_%s.json"

NAME = L('Title')
RE_DURATION = Regex('(?P<mins>[0-9]+):(?P<secs>[0-9]+)')

####################################################################################################
def Start():

	Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
	Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
	Plugin.AddViewGroup("Pictures", viewMode="Pictures", mediaType="photos")

	# Set the default ObjectContainer attributes
	ObjectContainer.title1 = NAME
	ObjectContainer.view_group = "List"

	# Set the default cache time
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:20.0) Gecko/20100101 Firefox/20.0"

####################################################################################################
@handler('/video/nationalgeographic', L('VideoTitle'))
def VideosMainMenu():

	oc = ObjectContainer()

	# Iterate over all of the available categories and display them to the user.
	categories = JSON.ObjectFromURL(JSON_CAT_URL)
	for category in categories['sectionlist']['section']:
		name = category['label']
		oc.add(DirectoryObject(key = Callback(ChannelVideoCategory, id = category['id'], name = CleanName(name)), title = name))

	return oc

####################################################################################################
@route('/video/nationalgeographic/{id}')
def ChannelVideoCategory(id, name, parent=''):

	oc = ObjectContainer()
	
	# Iterate over all the subcategories. It's possible that we actually find another sub-sub-category
	# In this case, we will simply recursively call this function again until we find actual playlists.
	sub_categories = JSON.ObjectFromURL(JSON_CHANNEL_CAT_URL % id)
	for sub_category in sub_categories['section']['children']:
		name = CleanName(sub_category['label'])

		has_child = sub_category['hasChild']
		if has_child == "true":
			oc.add(DirectoryObject(key = Callback(ChannelVideoCategory, id = sub_category['id'], name = name, parent=parent+'/'+id), title = name))
		else:
			oc.add(DirectoryObject(key = Callback(ChannelVideoPlaylist, id = sub_category['id'], name = name, parent=parent+'/'+id), title = name))

	# It's possible that there is actually no vidoes are available for the ipad. Unfortunately, they
	# still provide us with empty containers...
	if len(oc) < 1:
		return ObjectContainer(header=name, message="There are no titles available for the requested item.")

	return oc

####################################################################################################
@route('/video/nationalgeographic/{id}/playlist', allow_sync = True)
def ChannelVideoPlaylist(id, name, parent=''):

	oc = ObjectContainer(view_group="InfoList")

	# Iterate over all the available playlist and extract the available information.
	playlist = JSON.ObjectFromURL(JSON_PLAYLIST_URL % (id, str(0)))
	parent = parent + '/' + playlist['lineup']['id']
	for video in playlist['lineup']['video']:
		name = video['title'].replace('&#45;', '-')
		summary = video['caption']

		duration_text = video['time']
		try:
			duration_dict = RE_DURATION.match(duration_text).groupdict()
			mins = int(duration_dict['mins'])
			secs = int(duration_dict['secs'])
			duration = ((mins * 60) + secs) * 1000
		except:
			duration = 0

		# In order to obtain the actual url, we need to call the specific JSON page. This will also
		# include a high resolution thumbnail that can be used. We've found a small number of JSON
		# pages which don't actually include the URL link. We should try and detect these and simply
		# skip them.
		video_details = JSON.ObjectFromURL(JSON_VIDEO_URL % video['id'])
		url = BASE_URL + video_details['video']['url']
		if url == "http://video.nationalgeographic.com/video/player/":
			url = 'http://video.nationalgeographic.com/video/' + parent +'/' + video['id']
		else:
			url = url.rsplit('.html',1)[0] + '#BREADCRUMBS=/video' + parent +'/' + video['id']
		thumb = video_details['video']['still']
		if thumb.startswith("http://") == False:
			thumb = BASE_URL + thumb
		
		oc.add(VideoClipObject(
			url = url, 
			title = CleanName(name), 
			summary = String.StripTags(summary.strip()), 
			thumb = thumb,
			duration = duration
		))

	# It's possible that there is actually no vidoes are available for the ipad. Unfortunately, they
	# still provide us with empty containers...
	if len(oc) < 1:
		return ObjectContainer(header=name, message="There are no titles available for the requested item.")
	
	return oc

####################################################################################################
@handler('/photos/nationalgeographic', L('PhotosTitle'))

def PhotosMainMenu():
	oc = ObjectContainer(view_group='Pictures')
	
	feed = XML.ElementFromURL(POD_FEED, errors='ignore')
	for item in feed.xpath('//item'):
		title = item.xpath('./title')[0].text
		url = item.xpath('./guid')[0].text
		thumb = item.xpath('./enclosure')[0].get('url')
	
		
		# Ensure that we have a suitable description
		description = None
		if len(item.xpath('./description')) > 0:
			description = item.xpath('./description')[0].text
		if description == None:
			description = ""
		description = String.StripTags(description.strip())
	
		# Get the published date
		date = None
		try:
			date = Datetime.ParseDate(item.xpath('./pubdate')[0].text)
		except: pass
				
		oc.add(PhotoObject(
			url = url,
			title = title,
			summary = description,
			thumb = thumb,
			originally_available_at = date))
			
	return oc

####################################################################################################
def CleanName(name):

	# Function cleans up HTML ascii stuff	
	remove = [('&amp;','&'),('&quot;','"'),('&#233;','e'),('&#8212;',' - '),('&#39;','\''),('&#46;','.'),('&#58;',':'), ('&#8482;','')]
	for trash, crap in remove:
		name = name.replace(trash,crap)

	return name.strip()
