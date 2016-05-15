NAME = 'National Geographic'
VID_PREFIX = '/video/nationalgeographic'
PHOTO_PREFIX = '/photos/nationalgeographic'

POD_FEED = "http://feeds.nationalgeographic.com/ng/photography/photo-of-the-day/"
BASE_URL = "http://video.nationalgeographic.com"

####################################################################################################
def Start():

	# Set the default ObjectContainer attributes
	ObjectContainer.title1 = NAME

	# Set the default cache time
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:20.0) Gecko/20100101 Firefox/20.0"

####################################################################################################
@handler(VID_PREFIX, NAME + ' Videos')
def VideosMainMenu():

	oc = ObjectContainer()

	# Iterate over all of the available categories and display them to the user.
	oc.add(DirectoryObject(key = Callback(VideoCategory, title = 'All', url = BASE_URL), title = 'All'))
	categories = HTML.ElementFromURL(BASE_URL).xpath('//section[@id="grid-container"]//ul[@class="dropdown-menu"]/li/a')
	for category in categories:
		url = BASE_URL + category.xpath('./@href')[0]
		name = category.xpath('./text()')[0]
		oc.add(DirectoryObject(key = Callback(VideoCategory, title = name, url = url), title = name))

	return oc

####################################################################################################
@route(VID_PREFIX + '/category')
def VideoCategory(url, title):

	oc = ObjectContainer(title2=title)
	
	# Iterate over all the subcategories
	sub_categories = HTML.ElementFromURL(url).xpath('//section[@id="grid-container"]//ul[contains(@class, "grid-sections")]/li/a')
	for sub_category in sub_categories:
		# For some reason @href is picking up a lot of junk not seen in the code, so we have to cut it down
		url_ext = sub_category.xpath('./@href')[0].split('gs=')[1]
		section_url = '%s?gs=%s' %(url, url_ext)
		name = sub_category.xpath('./text()')[0]
		oc.add(DirectoryObject(key = Callback(VideoPlaylist, title = name, url = section_url), title = name))

	if len(oc) < 1:
		return ObjectContainer(header=name, message="There are no sections available for the requested item.")
	else:
		return oc

####################################################################################################
@route(VID_PREFIX + '/playlist', page = int)
def VideoPlaylist(url, title, page=0):

	oc = ObjectContainer(title2=title)

	local_url = '%s&gp=%s' %(url, str(page))
	section_name = title
	data = HTML.ElementFromURL(local_url)
	for video in data.xpath('//section[@id="grid-container"]//div[@class="media-module"]'):
		# Again adding junk to url so delete the extension here
		vid_url = BASE_URL + video.xpath('./a/@href')[0].split('?gc=')[0]
		# Skip links that are not videos
		if not '/video/' in vid_url:
			continue
		if not vid_url.startswith("http://"):
			vid_url = BASE_URL + vid_url
		thumb = video.xpath('.//img/@data-src')[0]
		if not thumb.startswith("http://"):
			thumb = BASE_URL + thumb
		name = video.xpath('./a/@data-title')[0]
		duration = video.xpath('./div[@class="timestamp"]//text()')[0].strip()
		try: duration = Datetime.MillisecondsFromString(duration)
		except: duration = None

		
		oc.add(VideoClipObject(
			url = vid_url, 
			title = name, 
			thumb = thumb,
			duration = duration
		))

	# Paging
	try: page = int(data.xpath('//a[contains(@class, "load-more")]/@href')[0].split('gp=')[1])
	except: page = None
	if page:
		oc.add(NextPageObject(key = Callback(VideoPlaylist, url=url, title=section_name, page=page), title = L("Next Page ...")))
	
	if len(oc) < 1:
		return ObjectContainer(header='Empty', message="There are no videos available for this category.")
	else:
		return oc

####################################################################################################
@handler(PHOTO_PREFIX, NAME + ' Photos')

def PhotosMainMenu():
	oc = ObjectContainer()
	
	feed = XML.ElementFromURL(POD_FEED, errors='ignore')
	for item in feed.xpath('//item'):
		title = item.xpath('./title')[0].text
		url = item.xpath('./feedburner:origLink' , namespaces={'feedburner':'http://rssnamespace.org/feedburner/ext/1.0'})[0].text
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
