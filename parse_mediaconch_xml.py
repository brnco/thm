'''
parses mediaconch XML and reports on unique values
'''

import pathlib
from bs4 import BeautifulSoup
import util

def parse_all_tag_values(kwargs):
    '''
    parses tag values from mediaconch
    '''
    taglist_to_delete = []
    for tag in kwargs.all_tag_values.keys():
        if len(set(kwargs.all_tag_values[tag])) > 1:
            #print(tag)
            #print(set(kwargs.all_tag_values[tag]))
            #print("")
            taglist_to_delete.append(tag)
    return taglist_to_delete

def get_tag_values(file,kwargs):
    '''
    iterates through mediaconch file and returns dict with all tags and all values
    '''
    with open(file,"r") as f:
        soup = BeautifulSoup(f)
    for tag in soup.find_all(r'rule'):
        try:
            tag_track = tag['value'] + "_" + tag['tracktype']
            kwargs.all_tag_values[tag_track].append(tag.string.strip())
        except KeyError as e:
            tag_track = tag['value'] + "_" + tag['tracktype']
            kwargs.all_tag_values[tag_track] = []
            kwargs.all_tag_values[tag_track].append(tag.string.strip())
    #print(kwargs.all_tag_values)
    return kwargs

def match_tag_track(tag):
    '''
    returns True if tag value = value from tag_track to delete
    returns false if not
    '''
    return tag['value'] 

def init():
    '''
    initialize variables and arguments
    '''
    kwargs = util.d({})
    kwargs.catalog_number = "A2022_034_001_001"
    kwargs.orig_xml_dir = pathlib.Path("/tub/brendan-project-archive/TheHistoryMakers/mediaconch/original/inputs") / kwargs.catalog_number
    kwargs.norm_xml_dir = pathlib.Path(str(kwargs.orig_xml_dir).replace("original","normalized"))
    kwargs.all_tag_values = util.d({})
    return kwargs

def main():
    '''
    do the thing
    '''
    kwargs = init()
    for file in kwargs.orig_xml_dir.iterdir():
        print(file)
        kwargs = get_tag_values(file, kwargs)
    taglist_to_delete = parse_all_tag_values(kwargs)
    tag_tracks_to_delete = []
    for tag_track in taglist_to_delete:
        tag = tag_track.replace("_Audio","").replace("_Video","").replace("_General","")
        track = tag_track.replace(tag + "_","")
        tag_tracks_to_delete.append([tag,track])
    for file in kwargs.orig_xml_dir.iterdir():
        print(type(file))
        print(type(kwargs.norm_xml_dir))
        file_normalized = str(kwargs.norm_xml_dir / file.stem) + ".mediaconch"
        print(str(file_normalized))
        input("eh")
        with open(file,"r+") as f:
            soup = BeautifulSoup(f)
            all_tags = soup.find_all(r'rule')
            for tag in all_tags:
                if tag['value'] in [i[0] for i in tag_tracks_to_delete]:
                    if tag['tracktype'] in [i[1] for i in tag_tracks_to_delete]:
                        print(tag.prettify())
                        tag.decompose()
        with open(str(file_normalized),"w+") as f:
            f.write(soup.prettify())


if __name__ == "__main__":
    main()

