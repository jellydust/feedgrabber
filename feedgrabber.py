import feedparser
import youtube_dl
import sqlite3
import time
import listparser as lp
import os.path

# The location of the DB
db_location = 'db.sqlite'

# Connect to the database (create if not found)
db = sqlite3.connect(db_location)
c = db.cursor()

# Create the subscription table in the db if it does not exist
c.execute('''
CREATE TABLE IF NOT EXISTS subscriptions (
  id integer PRIMARY KEY,
  name text NOT NULL UNIQUE,
  url text NOT NULL,
  videos text NOT NULL UNIQUE
)''')

# Create the preferences tables in the db if it does not exist
c.execute('''
CREATE TABLE IF NOT EXISTS preferences (
  if integer PRIMARY KEY,
  name text NOT NULL UNIQUE,
  value text NOT NULl
)''')

def import_feeds():
  '''Import feeds from Youtube's subscription_manager.xml file'''

  # Multiple prints, TODO: Is this efficient?
  print('\nThis will import all of your exported youtube subscriptions. ')
  print('0. Login to your Youtube account.')
  print('1. Go to https://www.youtube.com/subscription_manager ')
  print('2. Click "Export Subscriptions" at the bottom of the page.')
  print('3. Move the "subscription_manager.xml" file to the same folder as this script.')
  input('\nPress enter when ready to import.')
  filename = 'subscription_manager.xml'
  if os.path.isfile(filename):
    print('File found, continuing with import...')
  else:
    print('\nWARNING: File not found. "subscription_manager.xml" must be in the same directory as this script')
    print('Returning to main menu.')
    return

  d = lp.parse(filename)

  new_subs = 0

  for feed in d.feeds:

    # Check if the name contains valid characters
    videos_name = ''.join(e for e in feed.title if e.isalnum()) 

    for letter in videos_name:
      if ord(letter) < 48 or ord(letter) > 127:
        videos_name = videos_name.replace(letter,'x')

    already_subbed = list()
    

    c.execute('''SELECT name FROM subscriptions''')
    for row in c:
      if row[0].lower() == feed.title.lower():
        print ('  **WARNING: Entry {name} already exists; skipping'.format(name=feed.title))
        already_subbed.append(videos_name)
 
    if videos_name not in already_subbed:
      c.execute('''INSERT INTO subscriptions (name, url, videos)
                    VALUES(?, ?,?)''', (feed.title,feed.url,videos_name))

      create_table = '''
      CREATE TABLE {name} (
      title text NOT NULL UNIQUE,
      vidurl text NOT NULL,
      viewed integer NOT NULL)
      '''.format(name=videos_name)

      c.execute(create_table)

      d = feedparser.parse(feed.url) 
      for entry in d.entries: 
        title = '{title}-{pub}'.format(title=entry.title, pub=entry.published)
        c.execute('INSERT INTO '+videos_name+'(title, vidurl, viewed) VALUES (?, ?, ?)',(title, entry.link, 1))
      new_subs += 1

  db.commit()
  if new_subs > 0:
    print('Import complete! {num} subscriptions added. Run "list" to view all feeds.'.format(num=new_subs))
  else:
    print('No subscriptions were added.')



def add_sub():
  '''Allows the user to specify a name and url to subscribe to'''

  # Get the feed name and url from the user and verify that they are correct
  while True:
    table_name = input('Feed name: ')
    table_url = input('Feed URL: ')
    option = input('Do you want to mark all the videos being added as viewed? (y/N)')
    response = input('Name: {name} URL: {url} Viewed: {viewed} \nis this correct? (y/N/q): '.format(name=table_name, url=table_url, viewed=option))
    if response.lower() == 'y' or response.lower() == 'yes':
      break
    elif response.lower() == 'q' or response.lower() == 'quit':
      return

  # Check if feed is valid
  d = feedparser.parse(table_url) 
  if 'title' not in d.feed:
    option = input('WARNING: There are missing elements in the feed provided. Continue anyways? (y/N) ')
    if option.lower() != 'y':
      print('Aborting ...')
      return

  # A sanitized version of the entered name
  videos_name = ''.join(e for e in table_name if e.isalnum())
  #videos_name = ''.join([i if ord(i) < 128 else ' ' for i in videos_name])

  # Check if the name already exists in the database, if it does, return
  c.execute('''SELECT name FROM subscriptions''')
  for row in c:
    if row[0].lower() == table_name.lower():
      print ('\n**WARNING: Entry already exists; aborting operation\n')
      return
 
  c.execute('''INSERT INTO subscriptions (name, url, videos)
                  VALUES(?, ?,?)''', (table_name,table_url,videos_name))

  create_table = '''
  CREATE TABLE {name} (
  title text NOT NULL UNIQUE,
  vidurl text NOT NULL,
  viewed integer NOT NULL)
  '''.format(name=videos_name)

  c.execute(create_table)

  # Mark as viewed if the option was selected
  if option.lower() == 'yes' or option.lower() == 'y':
    for entry in d.entries: 
      title = '{title}-{pub}'.format(title=entry.title, pub=entry.published)
      c.execute('INSERT INTO '+videos_name+'(title, vidurl, viewed) VALUES (?, ?, ?)',(title, entry.link, 1))

  db.commit()
  print('Feed added to database.')



def list_subs():
  '''Queries the database and returns all saved subscriptions'''

  # First let's grab the number of subscriptions and display that
  # This is useful for other functions that rely on list_subs
  max_rows = c.execute('SELECT count(*) FROM subscriptions')
  max_rows_int = max_rows.fetchone()[0]
  print('There are {total_subs} subscriptions found.'.format(total_subs=max_rows_int))

  # This will not display if there are no rows found
  if max_rows_int != 0:
    print('[id] - [name] @ [url]')
  for row in c.execute('SELECT * FROM subscriptions'):
    print('{position}  - {name} @ {url}'.format(position=str(row[0]).ljust(4,' '), name=row[1], url=row[2]))




def remove_sub():
  '''Display all subscriptions and optionally delete one'''

  # Show all the subs that are currently in the database
  list_subs()

  # Dislay an error message if the database is empty
  max_rows = c.execute('SELECT count(*) FROM subscriptions')
  max_rows_int = max_rows.fetchone()[0]
  
  if max_rows_int == 0:
    print('There are no subscriptions in the database to remove.')
    return

  # Using the id, select which sub to delete
  not_found = True #double neg
  while not_found:
    option = input('Which subscription do you want to remove? [enter id or enter "cancel"] ')

    if option.lower() == 'cancel' or option.lower() == 'c':
      print('Cancelled.')
      return

    try:
      option_int = int(option)
    except ValueError:
      print('Value must be a number or "cancel".'.format(max=max_rows_int))
      continue

    # if option_int = row[0] continue
    for row in c.execute('SELECT id FROM subscriptions'):
      if row[0] == option_int:
        not_found = False

    if not_found:
      print('Subscription ID does not match anything available.')

  # Get the subscription name based on the row number
  get_sub_name = c.execute('SELECT name FROM subscriptions WHERE id = ?',(option_int,))

  for i in get_sub_name:
    sub_name = i[0]

  # Confirm deletion
  print('Are you sure you want to delete the following subscription? :')
  print(' {title}'.format(title=sub_name))
  answer = input('type "confirm" to accept, anything else to abort ')
  if answer.lower() == 'confirm':
    table_name_cursor = c.execute('SELECT videos FROM subscriptions WHERE id = ?',(option_int,))
    table_name = table_name_cursor.fetchone()
    command = 'DELETE FROM subscriptions WHERE id = {id}'.format(id=option_int)
    c.execute(command)
    c.execute('DROP TABLE '+table_name[0])
    db.commit()
    print('Feed removed from subscriptions.')
  else:
    print('Abort deletion.')


# The following pieces taken from the youtube-dl homepage
class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

# future: youtube-dl -ignore-errors --no-playlist --add-metadata --restrict-filenames --batch-file=test.txt --download-archive "here.txt" -f bestvideo[ext=mp4]+bestaudio[ext=m4a] --merge-output-format mp4 --write-thumbnail 
def progress_hook(feed):
  '''Watches for the 'finished' status from ydl to provide the filename to the user'''
  if feed['status'] == 'finished':
    print('Done downloading file: {filename}'.format(filename=feed['filename']))

# need to add ffmpeg
youtube_dl_flags = {
  'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]',
  'merge_output_format': 'mp4',
  'outtmpl': '%(uploader)s/%(upload_date)s - %(title)s.%(ext)s', 
  'ignoreerrors':'',
  'noplaylist':'',
  'download_archive': 'history.log',
  'logger': MyLogger(),
  'progress_hooks': [progress_hook],
}



def convert_to_hooktube(link):
  '''replace 'www.youtube.com' with 'hooktube.com' in the provided url'''
  return link.replace('www.youtube.com', 'hooktube.com')



def get_video(link, proxy=False):
  '''Download the video from the url provided'''
  if proxy:
    with youtube_dl.YoutubeDL(youtube_dl_flags) as ydl:
      ydl.download([convert_to_hooktube(link)])
  else:
    with youtube_dl.YoutubeDL(youtube_dl_flags) as ydl:
      ydl.download([link])  



def check_for_videos(viewed=False):
  subs = {}
  lima = c.execute('SELECT videos, url FROM subscriptions')
  for item in lima:
    subs[item[0]] = item[1]
  
  # Check for NEW videos
  for i, l in subs.items():

    print('  Checking {n} ...'.format(n=i))

    number_of_added_vids = 0

    d = feedparser.parse(l) 
    
    videos_list = c.execute('SELECT vidurl FROM '+i) 

    existing_videos = list()
    for row in videos_list:
      existing_videos.append(row[0])

    if viewed:
      viewed_flag = 1
    else:
      viewed_flag = 0

    for entry in d.entries:
      if entry.link not in existing_videos:
        number_of_added_vids += 1
        title = '{title}-{pub}'.format(title=entry.title, pub=entry.published)
        c.execute('INSERT INTO '+i+'(title, vidurl, viewed) VALUES (?, ?, ?)',(title, entry.link, viewed_flag))

    print('  {num} new videos added ...'.format(num=number_of_added_vids))

  # Commit the videos to the DB
  db.commit()




def download_all_videos(proxy=False):
  subs = {}
  lima = c.execute('SELECT videos, url FROM subscriptions')
  for item in lima:
    subs[item[0]] = item[1]
  # Download all videos whose viewed flag is 0
  for i, l in subs.items():
    
    videos_count = c.execute('SELECT count(*) FROM '+i+' WHERE viewed = 0')
    videos_count_int = int(videos_count.fetchone()[0])
    print('  Grabbing {count} videos for {name} ...'.format(count=videos_count_int, name=i))

    grabbed = 0

    c.execute('SELECT * FROM '+i)
    videos = c.fetchall()
    for row in videos:
      if row[2] == 0:
        if proxy:
          get_video(row[1])
        else:
          get_video(row[1], True)
        c.execute('UPDATE '+i+' SET viewed = 1 WHERE title like ?',(row[0],))
        grabbed += 1
        print('  {grabbed} grabbed of {total}.'.format(grabbed=grabbed, total=videos_count_int))

 # Commit the updated view table
  db.commit()


  
def watch_for_videos(proxy=False):
  '''Check for videos, download them, and then wait on a timer to check again'''
  print('Checking for videos ...')
  minute = 60
  timer = minute * 60
  while True:
    check_for_videos()
    if proxy:
      download_all_videos()
    else:
      download_all_videos(True)
    print('Sleeping for {time} minutes ...'.format(time=timer/minute))
    time.sleep(int(timer))
    print('Time elapsed, checking for videos ...')
 


def run_watcher(proxy=False):
  '''Run the watch_for_videos function but break with any keyboard interrupt'''
  print('Perform a keyboard interupt at any time to return to the main menu.')
  if proxy:
    try:
        watch_for_videos()
    except KeyboardInterrupt:
        print('\n\nInterupt received, returning to menu.')
  else:
    try:
        watch_for_videos(True)
    except KeyboardInterrupt:
        print('\n\nInterupt received, returning to menu.')



def create_rss_url():
  print('\n\nThis will help create a proper RSS feed URL for a Youtube channel')
  print('You will need either a Channel ID or a User ID')
  print('To get either, go to the default channel\'s main Youtube page and check the URL')
  print('\n  Channnel ID example: https://www.youtube.com/channel/[[UCwRXb5dUK4cvsHbx-rGzSgw]]')
  print('  User ID example: https://www.youtube.com/user/[[derekbanas]]')
  print('\nYou will need the part that is within the square [] brackets')

  keep_going = True
  while keep_going:
    option = input('\nDo you have a channel [1] or user [2] id? [cancel] ')

    if option.lower() == 'cancel' or option.lower() == 'c':
      print('Cancelled.')
      return 

    try:
      option_int = int(option)
    except ValueError:
      print('Value must be a number or "cancel".')
      continue

    if type(option_int) is int:
      keep_going = False

  if option_int == 1:
    option = input('Channel ID: ')
    print ('  Copy this ->  https://www.youtube.com/feeds/videos.xml?channel_id={id}'.format(id=option))
  elif option_int == 2:
    option = input('User ID: ')
    print('  Copy this ->  https://www.youtube.com/feeds/videos.xml?user={id}'.format(id=option))
  else:
    print('Selected option not available.')



def menu_help():
  '''Display the 'main menu' options'''
  print('Choose from the following bracket surrounded words to execute an action:')
  print('  [add] - to add a subscription feed')
  print('  [remove] - to remove a subscription feed')
  print('  [list] - lists all feeds')
  print('  [watcher] - watch for videos on a timer')
  print('  [watcherp] - watch for videos on a timer through Hooktube')
  print('  [run] - grab the latest videos')
  print('  [runp] - grab the latest videos through Hooktube')
  print('  [url] - helps create a Youtube RSS feed')
  print('  [import] - import a youtube subscription xml')
  print('  [quit] - exits the program')



def leave():
  '''Close the connection to the database and exit'''
  db.close()
  exit()


# Main menu
print('FEEDGRABBER')
while (True):
  option = input('Enter an option ([help] for options): ')
  option = option.lower()

  if option == 'add':
    add_sub()
  elif option == 'run':
    check_for_videos()
    download_all_videos()
  elif option == 'runp':
    check_for_videos()
    download_all_videos(True)
  elif option == 'watcher':
    run_watcher()
  elif option == 'watcherp':
    run_watcher(True)
  elif option == 'quit' or option == 'exit':
    leave()
  elif option == 'help':
    menu_help()
  elif option == 'url':
    create_rss_url()
  elif option == 'list':
    list_subs()
  elif option == 'remove':
    remove_sub()
  elif option == 'import':
    import_feeds()
  else:
    print('\nSelection not recognized.\n')
    menu_help()
