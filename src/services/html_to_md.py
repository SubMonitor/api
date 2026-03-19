import html2text

converter = html2text.HTML2Text()

converter.ignore_links = False
converter.ignore_images = True
converter.ignore_emphasis = False
converter.body_width = 0