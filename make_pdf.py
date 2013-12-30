#!/usr/bin/env python3

# Copyright © 2013 Jean-François Hren <jfhren@gmail.com>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file for more details.

import sys, os, errno, requests, subprocess
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image

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


def get_config(config_file):

    """Parse the config of the light novel."""

    with open(config_file) as conf_file:
        author = conf_file.readline().strip()
        main_title = conf_file.readline().strip()
        config = [{'url': line.split()[0], 'title': line[line.find(' '):].strip()} for line in conf_file.readlines() if line.strip()]

    return (author, main_title, config)


def get_template():

    """Parse the template files and return a dictionary of them."""

    with open('templates/latex_template_document') as template_file:
        template = {'document':template_file.read().split()}

    with open('templates/latex_template_replace') as template_file:
        template['replace'] = [(lambda x: x if len(x) == 2 else [x[0], ' '])(e.split()) for e in template_file.readlines()]

    with open('templates/latex_template_preamble') as preamble:
        template['preamble'] = preamble.read().format(author, main_title)

    with open('templates/latex_template_peroration') as peroration:
        template['peroration'] = peroration.read()

    return template


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


def get_image_angle(image_path):

    """Get an image angle depending on its geometry."""

    (width, height) = Image.open(image_path).size
    if width > height:
        return 90
    return 0


def parse_tag(tag, images, template, output_dir):

    """Parse a tag and child tags using the images and the latex template and return a string."""

    text = ''
    if tag.name == 'p':
        for elt in tag.contents:
            if isinstance(elt, NavigableString) and elt.string.strip():
                text += elt.string.strip()
            elif elt.name == 'b':
                text += template['document'][1].format(elt.string.strip())
            elif elt.name == 'i':
                text += template['document'][2].format(elt.string.strip())
        for replace_match in template['replace']:
            text = text.replace(replace_match[0], replace_match[1])
    elif tag.name == 'div':
        tag_img = tag.find(class_='thumbimage')
        if tag_img:
            image_name = tag_img['src']
            image_name = image_name[22:image_name.rfind('/')]

            if image_name in images:
                images.remove(image_name)

            text = template['document'][3].format(get_image_angle(os.path.join(output_dir, 'images/'+image_name[image_name.rfind('/')+1:])), './images/'+image_name[image_name.rfind('/')+1:])
    elif tag.name == 'center':
        text = template['document'][4].format(tag.string)
        for replace_match in template['replace']:
            text = text.replace(replace_match[0], replace_match[1])

    if text:
        text += '\n'

    return text


def generate_tex_file(url, output_dir, title, template):

    """Generate a tex file from a given url in a given output dir with a given title.tex filename."""

    try:
        os.mkdir(output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    # Get the html content of the url and parse it.
    html_content = requests.get(url).text
    soup = BeautifulSoup(html_content)

    # Get each chapter.
    chapter_headers = soup.find_all(class_='mw-headline')

    # Get the images from the illustration "chapter".
    images = [tag['src'][22:tag['src'].rfind('/')] for tag in chapter_headers[0].parent.find_next_sibling('ul').find_all('img')]

    get_images(os.path.join(output_dir, 'images'), images)

    # For each chapter (excluding the first), we get its contents.
    chapters = [{'title':chapter.string,
                 'content':[parse_tag(tag, images, template, output_dir) for tag in chapter.parent.next_siblings_until(['h2', 'h3','table']) if parse_tag(tag, images, template, output_dir)]
                } for chapter in chapter_headers[1:]]

    # Starting the tex file with the preamble.
    tex_file_content = template['preamble']

    # Then the left over images are added.
    for image in images:
        tex_file_content += template['document'][3].format(get_image_angle(os.path.join(output_dir, 'images/'+image[image.rfind('/')+1:])), './images/'+image[image.rfind('/')+1:])+'\n'

    # We go through the chapters and add each chapter title and content.
    for chapter in chapters:
        tex_file_content += template['document'][0].format(chapter['title'])
        for text in chapter['content']:
            tex_file_content += text + '\n'

    # Finally we add the peroration.
    tex_file_content += template['peroration']

    # The filename of the tex file.
    filename = os.path.join(output_dir, title+'.tex')

    # If the file already exists, we check if something changed.
    if os.path.exists(filename):
        with open(filename, mode='r', encoding='utf-8') as tex_file:
            previous_tex_file_content = tex_file.read()
            if previous_tex_file_content == tex_file_content:
                return False

    # If not we write the tex file.
    with open(filename, mode='w', encoding='utf-8') as tex_file:
        tex_file.write(tex_file_content)

    return True



def generate_pdf_file(output_dir, title):

    """Call pdflatex two times."""

    # We trash the outputs.
    null_output = open('/dev/null', 'w')
    subprocess.Popen(['pdflatex', title+'.tex'], stdout=null_output, stderr=null_output, cwd=output_dir)
    subprocess.Popen(['pdflatex', title+'.tex'], stdout=null_output, stderr=null_output, cwd=output_dir)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: {0} config_file'.format(sys.argv[0]))

    (author, main_title, config) = get_config(sys.argv[1])
    template = get_template()

    try:
        os.mkdir(main_title)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

    for volume in config:
        output_dir = os.path.join(main_title, volume['title'])

        if generate_tex_file(volume['url'], output_dir, volume['title'], template):
            generate_pdf_file(output_dir, volume['title'])
            print(volume['title'] + ' generated')
        else:
            print(volume['title'] + ' up-to-date.')
