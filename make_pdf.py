#!/usr/bin/env python3

# Copyright © 2013 Jean-François Hren <jfhren@gmail.com>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

import sys
import os
import errno
from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Tag
import requests

def next_siblings_until(self, stop_tags):

    """Define a new iterator class for bs4.element.Tag and return an instance of such a class."""

    gen = self.next_siblings

    class __next_siblings_until:

        """Define an iterator on Tag instances. The iterator stops when a Tag instance name attribute is in stop_tags."""

        def __iter__(self):
            return self

        def __next__(self):
            tag = next(gen)
            if tag.name in stop_tags:
                raise StopIteration
            return tag

    return __next_siblings_until()

Tag.next_siblings_until = next_siblings_until


def parse_tag(tag, images, template):

    """Parse a tag and child tags using the images and the latex template and return a string."""

    text = ''
    if tag.name == 'p':
        for elt in tag.contents:
            if isinstance(elt, NavigableString) and elt.string.strip():
                text += elt.string.strip()
            elif elt.name == 'b':
                text += template[1].format(elt.string.strip())
            elif elt.name == 'i':
                text += template[2].format(elt.string.strip())
        for replace_match in template[-1]:
            text = text.replace(replace_match[0], replace_match[1])
    elif tag.name == 'div':
        tag_img = tag.find(class_='thumbimage')
        if tag_img:
            image_name = tag_img['src']
            image_name = image_name[22:image_name.rfind('/')]

            if image_name in images:
                images.remove(image_name)

            text = template[3].format('./images/'+image_name[image_name.rfind('/')+1:])
    elif tag.name == 'center':
        text = template[4].format(tag.string)
        for replace_match in template[-1]:
            text = text.replace(replace_match[0], replace_match[1])

    if text:
        text += '\n'

    return text


def output_tex(filename, images, sections, template, author, main_title):

    """Output a tex file containing the images and sections."""

    with open(filename, mode='w', encoding='utf-8') as tex_file:
        with open('templates/latex_template_preamble') as preamble:
            tex_file.write(preamble.read().format(author, main_title))

        for image in images:
            tex_file.write(template[3].format('./images/'+image[image.rfind('/')+1:])+'\n')

        for section in sections:
            tex_file.write(template[0].format(section[0]))
            for text in section[-1]:
                tex_file.write(text)
                tex_file.write('\n')

        with open('templates/latex_template_peroration') as peroration:
            tex_file.write(peroration.read())

    print(filename+' written.')


def get_images(images_dir, images):

    """Create the output directory if necessary, fetch the images from Baka-Tsuki and put them in the output directory."""

    try:
        os.mkdir(images_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    listdir = os.listdir(images_dir)

    for image in images:
        filename = image[image.rfind('/')+1:]
        if filename not in listdir:
            with open(os.path.join(images_dir, filename), 'wb') as image_file:
                print('Getting '+filename+'...')
                image_file.write(requests.get('http://www.baka-tsuki.org/project/images/'+image).content)


def generate_tex(url, output_dir, author, main_title, title):

    """Generate a tex file from a given file."""

    try:
        os.mkdir(output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    with open('templates/latex_template_document') as template_file:
        template = template_file.read().split()
    with open('templates/latex_template_replace') as template_file:
        template.append([(lambda x: x if len(x) == 2 else [x[0], ' '])(e.split()) for e in template_file.readlines()])

    html_content = requests.get(url).text
    soup = BeautifulSoup(html_content)

    # Get each chapter.
    section_headers = soup.find_all(class_='mw-headline')

    # Get the images from the illustration "chapter".
    images = [tag['src'][22:tag['src'].rfind('/')] for tag in section_headers[0].parent.find_next_sibling('ul').find_all('img')]

    get_images(os.path.join(output_dir, 'images'), images)

    # For each chapter (excluding the first), we get its contents.
    sections = [(section.string,
                 [parse_tag(tag, images, template) for tag in section.parent.next_siblings_until(['h2', 'h3','table']) if parse_tag(tag, images, template)]
                ) for section in section_headers[1:]]

    output_tex(os.path.join(output_dir, title+'.tex'), images, sections, template, author, main_title)


def generate_pdf(output_dir, title):

    pid = os.fork()

    if pid == 0:
        os.chdir(output_dir)
        os.execlp('pdflatex', 'pdflatex', title+'.tex')

    os.waitpid(pid, 0)


def get_config(config_file):
    with open(config_file) as conf_file:
        author = conf_file.readline().strip()
        main_title = conf_file.readline().strip()
        config = [{'url': line.split()[0], 'title': line[line.find(' '):].strip()} for line in conf_file.readlines() if line.strip()]

    return (author, main_title, config)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: {0} config_file'.format(sys.argv[0]))

    (author, main_title, config) = get_config(sys.argv[1])

    try:
        os.mkdir(main_title)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    for volume in config:
        output_dir = os.path.join(main_title, volume['title'])
        generate_tex(volume['url'], output_dir, author, main_title, volume['title'])
        generate_pdf(output_dir, volume['title'])
        generate_pdf(output_dir, volume['title'])
