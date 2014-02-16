POD_FEED = "http://feeds.nationalgeographic.com/ng/photography/photo-of-the-day/"
BASE_URL = "http://video.nationalgeographic.com"
JSON_CAT_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/main_sections.json"
JSON_CHANNEL_CAT_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/category_%s.json"
JSON_PLAYLIST_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/lineup_%s_%s.json"
#JSON_VIDEO_URL = "http://video.nationalgeographic.com/video/player/data/mp4/json/video_%s.json"

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
		name = category['label'].replace(' Video', '')
		oc.add(DirectoryObject(key = Callback(ChannelVideoCategory, id = category['id'], name = String.DecodeHTMLEntities(name)), title = name))

	return oc

####################################################################################################
@route('/video/nationalgeographic/{id}')
def ChannelVideoCategory(id, name, parent=''):

	oc = ObjectContainer()
	
	# Iterate over all the subcategories. It's possible that we actually find another sub-sub-category
	# In this case, we will simply recursively call this function again until we find actual playlists.
	sub_categories = JSON.ObjectFromURL(JSON_CHANNEL_CAT_URL % id)
	for sub_category in sub_categories['section']['children']:
		name = String.DecodeHTMLEntities(sub_category['label'])

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
@route('/video/nationalgeographic/{id}/playlist', page = int, allow_sync = True)
def ChannelVideoPlaylist(id, name, parent='', page=0):

	oc = ObjectContainer(view_group="InfoList")

	# Unable to properly resolve the urls from the json, so from this point on we us html
	local_url = '%s/video/%s/%s/%s/' %(BASE_URL, parent, id, str(page))
	section_name = name
	data = HTML.ElementFromURL(local_url)
	for video in data.xpath('//ul[contains(@class,"grid")]/li/div[@class="vidthumb"]'):
		try: lock = video.xpath('./span[@class="vidtimestamp"]/span/@class')[0]
		except: lock = None
		# Skip locked videos
		if lock:
			continue
		url = BASE_URL + video.xpath('./a/@href')[0]
		if not url.startswith("http://"):
			url = BASE_URL + url
		thumb = video.xpath('.//img/@src')[0]
		if not thumb.startswith("http://"):
			thumb = BASE_URL + thumb
		name = String.DecodeHTMLEntities(video.xpath('./a/@title')[0])
		duration = video.xpath('./span[@class="vidtimestamp"]//text()')[0].strip()
		try: duration = Datetime.MillisecondsFromString(duration)
		except: duration = None

		
		oc.add(VideoClipObject(
			url = url, 
			title = name, 
			thumb = thumb,
			duration = duration
		))

	# Paging
	pages = data.xpath('.//nav[contains(@class, "pagination")]/li/a//text()')
	for item in pages:
		if 'Next' in item:
			page = page + 1
			oc.add(NextPageObject(key = Callback(ChannelVideoPlaylist, id=id, parent=parent, name=section_name, page=page), title = L("Next Page ...")))
	
	# It's possible that there is actually no vidoes are available for the ipad. Unfortunately, they
	# still provide us with empty containers...
	if len(oc) < 1:
		return ObjectContainer(header=name, message="There are no videos available for this category.")
	
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
