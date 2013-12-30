baka_tsuki_script
=================

A python script to fetch light novels translations and images from Baka-Tsuki
and generate pdf file using pdflatex.

## Requirements

I wrote it with Python3 in mind so I do not know with Python2. BeautifulSoup4,
requests and pillow (PIL for Python3) are imported and thus needed.

## Usage

The script need a config file information about the light novel and the url for
each volume and their titles:  `
./make_pdf.py some_file_with_config`
I only tested the script for Chrome Shelled Regios and Mahouka Koukou no
Rettousei, so I am not sure it works correctly for other light novels on
Baka-Tsuki.
The script downloads the necessary images if not present. If a previous .tex
file is found, it is tested again the newly generated .tex file and if no change
is found, the pdf is not generated (since it is useless).


## Futur Improvements

Moving away from latex and generating mobi files instead.
