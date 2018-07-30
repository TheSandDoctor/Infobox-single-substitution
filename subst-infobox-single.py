#!/usr/bin/env python3.6
import time,mwclient
def getTransclusions(site,page,sleep_duration = None,extra=""):
    cont = None;
    pages = []
    i = 1
    while(1):
        result = site.api('query',list='embeddedin',eititle=str(page),eicontinue=cont,eilimit=500,format='json')
        print("got here")
        if sleep_duration is (not None):
            time.sleep(sleep_duration)
        #res2 = result['query']['embeddedin']
        for res in result['query']['embeddedin']:
            print('append ' + res['title'])
            pages.append(res['title'])
            i +=1
        try:
            cont = result['continue']['eicontinue']
            print("cont")
        except NameError:
            print("Namerror")
            return [pages,i]
        except Exception as e:
            print("Other exception" + str(e))
        #    print(pages)
            return [pages,i]

#getTransclusions(site,"Template:GA Nominee") + "\n"

import configparser, mwparserfromhell, argparse,re, pathlib, json
from time import sleep

def call_home(site):
    page = site.Pages['User:DeprecatedFixerBot/status']
    text = page.text()
    data = json.loads(text)["run"]["subst_infobox_single"]
    if str(data) == str(True):
        return True
    return False
def allow_bots(text, user):
    user = user.lower().strip()
    text = mwparserfromhell.parse(text)
    for tl in text.filter_templates():
        if tl.name in ('bots', 'nobots'):
            break
    else:
        return True
    for param in tl.params:
        bots = [x.lower().strip() for x in param.value.split(",")]
        if param.name == 'allow':
            if ''.join(bots) == 'none': return False
            for bot in bots:
                if bot in (user, 'all'):
                    return True
        elif param.name == 'deny':
            if ''.join(bots) == 'none': return True
            for bot in bots:
                if bot in (user, 'all'):
                    return False
    return True
def save_edit(page, utils, text):
    config = utils[0]
    
    site = utils[1]
    dry_run = utils[2]
    original_text = text
    if not dry_run:
        if not allow_bots(original_text, config.get('enwikidep','username')):
            print("Page editing blocked as template preventing edit is present.")
            return
    #print("{}".format(dry_run))
    code = mwparserfromhell.parse(text)
    for template in code.filter_templates():
        if template.name.matches("nobots") or template.name.matches("Wikipedia:Exclusion compliant"):
            if template.has("allow"):
                if "DeprecatedFixerBot" in template.get("allow").value:
                    break # can edit
            print("\n\nPage editing blocked as template preventing edit is present.\n\n")
            return
    if not call_home(site):#config):
        raise ValueError("Kill switch on-wiki is false. Terminating program.")
    time = 0
    edit_summary = """'Substituted [[Template:Infobox single]] or one of its redirects using [[User:""" + config.get('enwikidep','username') + "| " + config.get('enwikidep','username') + """]]. Questions? [[User talk:TheSandDoctor|msg TSD!]] (please mention that this is task #6! [[Wikipedia:Bots/Requests for approval/DeprecatedFixerBot 6|BRFA in-progress]])"""
    while True:
        #text = page.edit()
        if time == 1:
            text = site.Pages[page.page_title].text()
        try:
            content_changed, text = process_page(original_text,dry_run)
        except ValueError as e:
            """
                To get here, there must have been an issue figuring out the
                contents for the parameter colwidth.
                
                At this point, it is safest just to print to console,
                record the error page contents to a file in ./errors and append
                to a list of page titles that has had
                errors (error_list.txt)/create a wikified version of error_list.txt
                and return out of this method.
                """
            print(e)
            pathlib.Path('./errors').mkdir(parents=False, exist_ok=True)
            title = get_valid_filename(page.page_title)
            text_file = open("./errors/err " + title + ".txt", "w")
            text_file.write("Error present: " +  str(e) + "\n\n\n\n\n" + text)
            text_file.close()
            text_file = open("./errors/error_list.txt", "a+")
            text_file.write(page.page_title + "\n")
            text_file.close()
            text_file = open("./errors/wikified_error_list.txt", "a+")
            text_file.write("#[[" + page.page_title + "]]" + "\n")
            text_file.close()
            return
        try:
            if dry_run:
                print("Dry run")
                #Write out the initial input
                title = get_valid_filename(page.page_title)
                text_file = open("./tests/in " + title + ".txt", "w")
                text_file.write(original_text)
                text_file.close()
                #Write out the output
                if content_changed:
                    title = get_valid_filename(page.page_title)
                    text_file = open("./tests/out " + title + ".txt", "w")
                    text_file.write(text)
                    text_file.close()
                else:
                    print("Content not changed, don't print output")
                break
            else:
                #print("Would have saved here")
                page.save(text,summary=edit_summary,bot=True,minor=True)
                print("Saved page")
                if time == 1:
                    time = 0
                break
#TODO: Enable
#    page.save(text, summary=edit_summary, bot=True, minor=True)
#    print("Saved page")
        except [[EditError]]:
            print("Error")
            time = 1
            sleep(5)   # sleep for 5 seconds before trying again
            continue
        except [[ProtectedPageError]]:
            print('Could not edit ' + page.page_title + ' due to protection')
        break
def get_valid_filename(s):
    """
        Turns a regular string into a valid (sanatized) string that is safe for use
        as a file name.
        Method courtesy of cowlinator on StackOverflow
        (https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename)
        @param s String to convert to be file safe
        @return File safe string
        """
    assert(s is not "" or s is not None)
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def process_page(text,dry_run):
    wikicode = mwparserfromhell.parse(text)
    templates = wikicode.filter_templates()
    content_changed = False
    
    
    code = mwparserfromhell.parse(text)
    for template in code.filter_templates():
        if (template.name.matches("infobox single") or template.name.matches("info box single")
            or template.name.matches("infobox singles") or template.name.matches("single infobox")):
            try:
                template.name = "subst:" + "Infobox single"+ "|"
                content_changed = True
                print("content changed? " + str(content_changed))
            except ValueError:
                raise
    return [content_changed, str(code)] # get back text to save

def single_run(title, utils, site):
    if title is None or title is "":
        raise ValueError("Category name cannot be empty!")
    if utils is None:
        raise ValueError("Utils cannot be empty!")
    if site is None:
        raise ValueError("Site cannot be empty!")
    print(title)
    page = site.Pages[title]#'3 (Bo Bice album)']
    text = page.text()

    try:
        utils = [config,site,dry_run]
        save_edit(page, utils, text)#config, api, site, text, dry_run)#, config)
    except ValueError as err:
        print(err)
def list_run(list_to_run, utils, site, offset,limited_run,pages_to_run):
    if utils is None:
        raise ValueError("Utils cannot be empty!")
    if site is None:
        raise ValueError("Site cannot be empty!")
    if offset is None:
        raise ValueError("Offset cannot be empty!")
    if limited_run is None:
        raise ValueError("limited_run cannot be empty!")
    if pages_to_run is None:
        raise ValueError("""Seriously? How are we supposed to run pages in a
            limited test if none are specified?""")
    counter = 0
    # pages = site.Pages[list_to_run]
    for page1 in list_to_run:
        if offset > 0:
            offset -= 1
            print("Skipped due to offset config")
            continue
        print("Working with: " + str(page1) + " " + str(counter))
        page = site.Pages[page1]
        if limited_run:
            if counter < pages_to_run:
                counter += 1
                text = page.text()
                try:
                    save_edit(page, utils, text)#config, api, site, text, dry_run)#, config)
                except ValueError as err:
                    print(err)
            else:
                return  # run out of pages in limited run

def main():
    dry_run = False
    pages_to_run = 10
    offset = 0
    
    limited_run = True
    
    parser = argparse.ArgumentParser(prog='DeprecatedFixerBot Infobox Single substituter', description='''Adds "subst:" to the beginning of all
        {{infobox single}} and its redirects/aliases.''')
    parser.add_argument("-dr", "--dryrun", help="perform a dry run (don't actually edit)",
                        action="store_true")
                        #parser.add_argument("-arch","--archive", help="actively archive Tweet links (even if still live links)",
                        #                action="store_true")
    args = parser.parse_args()
    if args.dryrun:
        dry_run = True
        print("Dry run")

    site = mwclient.Site(('https','en.wikipedia.org'), '/w/')
    if dry_run:
        pathlib.Path('./tests').mkdir(parents=False, exist_ok=True)
    config = configparser.RawConfigParser()
    config.read('credentials.txt')
    try:
        #pass
        site.login(config.get('enwikidep','username'), config.get('enwikidep', 'password'))
    except errors.LoginError as e:
        #print(e[1]['reason'])
        print(e)
        raise ValueError("Login failed.")
        
    utils = [config,site,dry_run]
    try:
        list1 = getTransclusions(site,"Template:Infobox single")
        list2 = getTransclusions(site,"Template:Info box single")
        list3 = getTransclusions(site,"Template:Infobox Single")
        list4 = getTransclusions(site,"Template:Infobox Singles")
        list5 = getTransclusions(site,"Template:Single Infobox")
        list6 = getTransclusions(site,"Template:Single infobox")
        #joined_list = list1 + list2 + list3 + list4 + list5 + list6
        joined_list = [y for x in [list1, list2, list3, list4, list5, list6] for y in x]
        del list1
        del list2
        del list3
        del list4
        del list5
        del list6
        #single_run('User:DeprecatedFixerBot/sandbox', utils, site)
        list_run(joined_list[0], utils, site, offset,limited_run,pages_to_run)
#print(joined_list[0])
    except ValueError as e:
        print("\n\n" + str(e))

if __name__ == "__main__":
    main()
