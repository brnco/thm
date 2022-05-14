'''
parses mediaconch XML and reports on unique values
'''
from bs4 import BeautifulSoup
import util

def init():
    '''
    initialize variables and arguments
    '''
    kwargs = util.d({})
    kwargs.catalog_number = "A2022_034_001_001"
    return kwargs

def main():
    '''
    do the thing
    '''
    kwargs = init()
    print(kwargs.catalog_number)

if __name__ == "__main__":
    main()

