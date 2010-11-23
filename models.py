from appengine_django import models
from google.appengine.ext import db

class Page(models.BaseModel):
  path = db.TextProperty(required=True)
  title = db.TextProperty(required=False)
  header = db.TextProperty(required=False)
  description = db.TextProperty(required=False)
  keywords = db.TextProperty(required=False)
  
  def by_path(path):
    pages = Page.all().filter('path = ', path).fetch(1)
    if len(pages) < 1:
        page = Page(path = path)
        page.put()
        return page
    return pages[0]

  by_path = staticmethod(by_path)

  def save(quote):
    query = db.Query(Quote)
    query.filter("symbol =", quote.symbol)
    query.filter("date =", quote.date)
    if query.get() is None:
      quote.put()
      return True
    else:
      return False
