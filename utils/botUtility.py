from random import randint

YOUTUBE_CHECK = 'https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v='
PATH_RSPS_PEDIA = 'data/responsesPedia.tsv'
PATH_DESC_PEDIA = 'data/descPedia.tsv'
PATH_VIDEOS_LIB = 'data/videosLibrary.tsv'

def random_cal( day, time, calstr = None ):
    if calstr == None:
        calstr = ''
    time -= 1

    r = randint( 1, 4 )

    n = randint( 1, 10 )

    if r == 1:
        day += n
        calstr = f' - {str(n)}){calstr}'
    if r == 2:
        day -= n
        calstr = f' + {str(n)}){calstr}'
    if r == 3:
        day *= n
        calstr = f' / {str(n)}{calstr}'
    if r == 4:
        day /= n
        calstr = f' * {str(n)}{calstr}'

    if time > 0:
        return random_cal( day, time, calstr )
    
    return ( '(' * calstr.count(')') ) + f'{day}{calstr}'

def videoHttpToId( http ):
    videoId = http
    if http.startswith('http') or http.startswith('v='):
        if http.find('youtu.be') != -1:
            videoId = http[-11:]
        else:
            i = http.find('v=')
            if i+13 <= len(http):
                videoId = http[i+2:i+13]
            else:
                videoId = None
    
    return videoId