"""
Randomly downloaded as a script from the internet. Probably flakey.

Supports the responsive embedding of web videos URLs (currently YouTube and
Vimeo are supported) using the flex-video method.  Flex-video provides an
 intrinsic ratio that will properly scale your video on any device.
"""
import markdown

try:
    from markdown.util import etree
except:    
    from markdown import etree

version = "0.0.1"

class VideoExtension(markdown.Extension):
    def __init__(self, configs): 
        self.config = {
            'orientation':['Normal','screen orientation widescreen or None'],
            'provider':['YouTube','Provider youtube or vimeo']

        }

        # Override defaults with user settings
        if configs:
            for key, value in configs:
                self.setConfig(key, value)

    def add_inline(self, md, name, klass, re):
        pattern = klass(re)
        pattern.md = md
        pattern.ext = self
        md.inlinePatterns.add(name, pattern, "<reference")

    def extendMarkdown(self, md, md_globals):
        self.add_inline(md, 'vimeo', Vimeo,
            r'([^(]|^)(http|https)://(www.|)vimeo\.com/(?P<vimeoid>\d+)\S*')
        self.add_inline(md, 'youtube', Youtube,
            r'([^(]|^)(http|https)://www\.youtube\.com/watch\?\S*v=(?P<youtubeargs>[A-Za-z0-9_&=-]+)\S*')

class Vimeo(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://player.vimeo.com/video/%s?byline=0&amp;portrait=0' % m.group('vimeoid')
        width = "560"
        height = "315"
        return flex_video(url, width, height)


class Youtube(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://www.youtube-nocookie.com/embed/%s' % m.group('youtubeargs')
        orientation=self.ext.config['orientation'][0]
        provider=self.ext.config['provider'][0]
        if provider.lower() == 'youtube':
            if orientation.lower() == 'widescreen':
                width = "560"
                height = "315"
            else:
                width = "420"
                height = "315"  
        else:
            width="560"
            height="225"
                
        return flex_video(url, width, height)
    
def flex_video(url,width,height):
    """
    <div class="flex-video">
     <iframe width="420" height="315" src="http://www.youtube.com/embed/9otNWTHOJi8" frameborder="0" allowfullscreen></iframe>
   </div>    
    """
    obj=etree.Element('div')
    obj.set('class',"flex-video")
    iframe=etree.Element('iframe')
    iframe.set('width',width)
    iframe.set('height',height)
    iframe.set('src',url)
    iframe.set('frameborder',"0")
    obj.append(iframe)
    return obj
    

def makeExtension(configs=None) :
    return VideoExtension(configs=configs)
