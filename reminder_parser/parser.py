import re
import os
import logging
import datetime
import argparse
from datetime import date

'''
Bug: if yaml formatter has other contents, like, has a tag or date or author,
but no review info, there will be an error in Reminder.read()
'''

__version__ = '1.0.0'

#  logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


REVIEW_DURATION = {'1':1, '2':3, '3':7, '4':14, '5':30, '6':60, '7':90, '8':90}


class Reminder:
    def __init__(self):
        self.today = date.today()
        self.review_need = False
        self.review_times = 1
        self.review_day = self.today

    def calc_next_review_date(self, times):
        duration = 0
        if str(times) not in REVIEW_DURATION.keys():
            duration = REVIEW_DURATION['8']
        else:
            duration = REVIEW_DURATION[str(times)]

        return self.today + datetime.timedelta(days=duration)

    def get_yaml_formatter(self, f):
        patt_yaml = re.compile('---\n((.|\n)+)---')

        with open(f, 'r+') as fs:
            text = ''.join(fs.readlines(100))
            #  print(text)

            content =  re.match(patt_yaml, text)
            if content == None:
                return None

            return content.group(1)
    
    def get_yaml_index(self, content, pattern):

        element = [re.match(pattern, con) for con in content]
        element = list(filter(lambda x: x != None, element))[0]
        try:
            index = content.index(element.group(0))
        except:
            index = None

        return index

    def get_yaml_element(self, content, pattern):

        try:
            element = [re.match(pattern, con) for con in content]
            element = list(filter(lambda x: x != None, element))[0]
            return element.group(1)
        except:
            return None

    def get_review_info(self, content):
        patt_need = re.compile('Review_need: (.*)')
        patt_date = re.compile('Review_date: (.*)')
        patt_times = re.compile('Review_times: (.*)')

        #  ori_content = self.get_yaml_formatter(f)
        #  if ori_content == None:
            #  return

        content = content.split("\n")

        need = self.get_yaml_element(content, patt_need)
        last_date = self.get_yaml_element(content, patt_date)
        last_times = self.get_yaml_element(content, patt_times)

        logger.debug("Need review? {}".format(need))
        logger.debug("Last review date:{}".format(last_date))
        logger.debug("Last review times:{}".format(last_times))

        return need, last_date, last_times

    def write_review_info(self, f, content, need, date, times):
        patt_need = re.compile('Review_need: (.*)')
        patt_date = re.compile('Review_date: (.*)')
        patt_times = re.compile('Review_times: (.*)')

        new_content = content.split('\n')

        need_index = self.get_yaml_index(new_content, patt_need)
        if need_index == None:
            return None

        date_index = self.get_yaml_index(new_content, patt_date)
        if date_index == None:
            return None

        times_index = self.get_yaml_index(new_content, patt_times)
        if times_index == None:
            return None

        new_content[need_index] = 'Review_need: {}'.format(need)
        new_content[date_index] = 'Review_date: {}'.format(date)
        new_content[times_index] = 'Review_times: {}'.format(times)
        new_content = '\n'.join(new_content)

        with open(f, 'r+') as fs:
            newtext = fs.read().replace(content, new_content)

        with open(f, 'w') as fs:
            fs.write(newtext)


    def refresh(self, f):
        content = self.get_yaml_formatter(f)
        if content == None:
            return False

        need, last_date, last_times = self.get_review_info(content)
        if need == 'Fasle':
            return False

        next_review_times = int(last_times) + 1
        next_review_date = self.calc_next_review_date(next_review_times)
        logger.debug("next review date:{}, review times:{}".format(next_review_date, next_review_times))

        self.write_review_info(f, content, need, next_review_date, next_review_times)

        return True

    def read(self, f):
        content = self.get_yaml_formatter(f)
        if content == None:
            return None

        need, last_date, last_times = self.get_review_info(content)

        return [need, last_date, last_times]

    def start_review(self, f): 
        content = self.get_yaml_formatter(f)
        if content == None:
            return False

        logger.debug("start review, date:{}, review times:{}".format(self.today, 1))
        self.write_review_info(f, content, 'True', self.today + datetime.timedelta(days=1), 1)

        return True

    def add_yaml_formatter(self, f):
        content = self.get_yaml_formatter(f)
        if content != None:
            return

        content = []

        content.append('---')
        content.append('Review_need: {}'.format('Fasle'))
        content.append('Review_date: {}'.format(self.today))
        content.append('Review_times: {}'.format(1))
        content.append('---\n')
        content = '\n'.join(content)

        with open(f, 'r+') as fs:
            text = fs.read()

        with open(f, 'w') as fs:
            fs.write(content + text)


class FileOp:
    def __init__(self):
        self.ignore_file = ['.DS_Store', '.assert']
        self.file = []

    def traverse(self, path, filter_func=None):
        filter_file = []
        for fs in os.listdir(path):
            abs_fs = os.path.abspath(path + '/' + fs)
            logger.debug("search file: {}".format(fs))

            if fs in  self.ignore_file:
                continue
            
            if os.path.isdir(abs_fs):
                filter_file += self.traverse(abs_fs, filter_func)
            else:
                filename, file_extension = os.path.splitext(fs)
                if file_extension != '.md':
                    continue

                if filter_func != None \
                    and filter_func(abs_fs) == True:
                    filter_file.append(abs_fs)

        return filter_file

    def filter_today(self, f):
        reminder = Reminder()
        review = reminder.read(f)
        if review == None:
            return False

        review_date = datetime.datetime.strptime(review[1], '%Y-%m-%d').date()

        if review[0] == 'True' and (reminder.today - review_date).days >= 0:
            return True
        else:
            return False

    def filter_yaml_formatter(self, f):
        reminder = Reminder()
        review = reminder.read(f)
        if review == None:
            logger.debug("no review info, add new")
            reminder.add_yaml_formatter(f)

        return True

    def get_today_remind(self, path):
        files = self.traverse(path, self.filter_today)
        for f in files:
            logger.info('\'' + f + '\'')

    def format_file(self, path):
        files = self.traverse(path, self.filter_yaml_formatter)

    def start_review(self, files):
        reminder = Reminder()
        for f in files:
            ret = reminder.start_review(f)
            if ret == False:
                logger.error("Fatal!!! can't start a review: {}".format(f))
                continue
            logger.debug("start a review at: {}".format(f))

    def finish_review(self, files):
        reminder = Reminder()
        for f in files:
            ret = reminder.refresh(f)
            if ret == False:
                logger.error("Fatal!!! can't finish a review: {}".format(f))
                continue
            logger.debug("finish a review at: {}".format(f))


if __name__ == '__main__':
    op = FileOp()
    path = './'
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true', help='show version')
    parser.add_argument('-s', '--show', action='store_true', help='show today\'s review')
    parser.add_argument('-f', '--format', action='store_true', help='add yaml formatter')
    parser.add_argument('-n', '--new', nargs='*', help='start a new review')
    parser.add_argument('-r', '--review', nargs='*', help='had finished a review')
    args = parser.parse_args()

    if args.show == True:
        op.get_today_remind(path)

    if args.version == True:
        print("version {}".format(__version__))

    if args.new != None:
        op.start_review(args.new)

    if args.format == True:
        logger.info("Ready to format files")
        op.format_file(path)
        logger.info("Finish formatting files")

    if args.review != None:
        op.finish_review(args.review)
