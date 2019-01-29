# Copyright 2016 Jochen Schroeder
#
# This file is distributed under the terms of the
# GPLv3 licence. See the COPYING file for details

from __future__ import print_function
import sqlite3
try:
    from urllib.parse import unquote, urlparse
except:
    from urlparse import urlparse
    from urllib import unquote
import os
import tempfile
import sys
import pdfannotation
import PyPDF2
import warnings
from dateutil import parser as dtparser

global OVERWRITE_PDFS
OVERWRITE_PDFS = False

global PRESERVE_TREE
PRESERVE_TREE = False


def convert2datetime(s):
    return dtparser.parse(s)

def converturl2abspath(url):
    """Convert a url string to an absolute path"""
    try:
        pth = unquote(urlparse(url).path) #this is necessary for filenames with unicode strings
        print("Found %s"%pth)
    except:
        pth = unquote(str(urlparse(url).path)).decode("utf8") #this is necessary for filenames with unicode strings
        print("Found UTF-8 encoded %s"%pth.encode("utf8"))
    return os.path.abspath(pth)

def get_highlights_from_db(db, results={}):
    """Extract the locations of highlights from the Mendeley database
    and put results into dictionary.

    Parameters
    ==========
    db :    sqlite3.connection
        Mendeley sqlite database
    results : dict, optional
        Dictionary to hold the results. Default is an empty dictionary.

    Returns
    =======
    results : dict
        dictionary containing the query results
    """
    query = """SELECT Files.localUrl, FileHighlightRects.page,
                            FileHighlightRects.x1, FileHighlightRects.y1,
                            FileHighlightRects.x2, FileHighlightRects.y2,
                            FileHighlights.createdTime, FileHighlights.color
                    FROM Files
                    LEFT JOIN FileHighlights
                        ON FileHighlights.fileHash=Files.hash
                    LEFT JOIN FileHighlightRects
                        ON FileHighlightRects.highlightId=FileHighlights.id
                    WHERE (FileHighlightRects.page IS NOT NULL)"""
    ret = db.execute(query)
    for r in ret:
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [[r[2], r[3], r[4], r[5]]]
        cdate = convert2datetime(r[6])
        color = r[7]
        hlight = {"rect": bbox, "cdate": cdate, "color": color}
        if pth in results:
            if pg in results[pth]:
                if 'highlights' in results[pth][pg]:
                    results[pth][pg]['highlights'].append(hlight)
                else:
                    results[pth][pg]['highlights'] = [hlight]
            else:
                results[pth][pg] = {'highlights': [hlight]}
        else:
            results[pth] = {pg: {'highlights':[hlight]}}
    return results

def get_notes_from_db(db, results={}):
    """Extract notes from the Mendeley database
    and put results into dictionary.

    Parameters
    ==========
    db :    sqlite3.connection
        Mendeley sqlite database
    results : dict, optional
        Dictionary to hold the results. Default is an empty dictionary.

    Returns
    =======
    results : dict
        dictionary containing the query results
    """
    query = """SELECT Files.localUrl, FileNotes.page,
                            FileNotes.x, FileNotes.y,
                            FileNotes.author, FileNotes.note,
                            FileNotes.modifiedTime, FileNotes.color
                    FROM Files
                    LEFT JOIN FileNotes
                        ON FileNotes.fileHash=Files.hash
                    WHERE FileNotes.page IS NOT NULL"""
    ret = db.execute(query)
    for r in ret:
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [r[2], r[3], r[2]+30, r[3]+30] # needs a rectangle however size does not matter
        author = r[4]
        txt = r[5]
        cdate = convert2datetime(r[6])
        color = r[7]
        note = {"rect": bbox, "author": author, "content": txt, "cdate":cdate, "color": color}
        if pth in results:
            if pg in results[pth]:
                if 'notes' in results[pth][pg]:
                    results[pth][pg]['notes'].append(note)
                else:
                    results[pth][pg]['notes'] = [note]
            else:
                results[pth][pg] = {'notes': [note]}
        else:
            results[pth] = {pg: {'notes':[note]}}
    return results

def add_annotation2pdf(inpdf, outpdf, annotations):
    for pg in range(1, inpdf.getNumPages()+1):
        inpg = inpdf.getPage(pg-1)
        if pg in annotations.keys():
            if 'highlights' in annotations[pg]:
                for hn in annotations[pg]['highlights']:
                    if hn['color'] is not None:
                        annot = pdfannotation.highlight_annotation(hn["rect"], cdate=hn["cdate"], color=hn["color"])
                    else:
                        annot = pdfannotation.highlight_annotation(hn["rect"], cdate=hn["cdate"])
                    pdfannotation.add_annotation(outpdf, inpg, annot)
            if 'notes' in annotations[pg]:
                for nt in annotations[pg]['notes']:
                    if nt['color'] is not None:
                        note = pdfannotation.text_annotation(nt["rect"], contents=nt["content"], author=nt["author"],
                                                             color=nt["color"], cdate=nt["cdate"])
                    else:
                        note = pdfannotation.text_annotation(nt["rect"], contents=nt["content"], author=nt["author"],
                                                             cdate=nt["cdate"])
                    pdfannotation.add_annotation(outpdf, inpg, note)
        outpdf.addPage(inpg)
    return outpdf

def processpdf(fn, fn_out, annotations):
    try:
        inpdf = PyPDF2.PdfFileReader(open(
            fn.encode(sys.getfilesystemencoding()), 'rb'), strict=False)
        if inpdf.isEncrypted:
            # PyPDF2 seems to think some files are encrypted even
            # if they are not. We just ignore the encryption.
            # This seems to work for the one file where I saw this issue
            inpdf._override_encryption = True
            inpdf._flatten()
    except IOError:
        print("Could not find pdffile %s"%fn.encode(sys.getfilesystemencoding()))
        return
    outpdf = PyPDF2.PdfFileWriter()
    outpdf = add_annotation2pdf(inpdf, outpdf, annotations)
    if os.path.isfile(fn_out.encode(sys.getfilesystemencoding())):
        if not OVERWRITE_PDFS:
            print("%s exists skipping"%fn_out.encode(sys.getfilesystemencoding()))
            return
        else:
            print("overwriting %s"%fn_out.encode(sys.getfilesystemencoding()))
            # use temporary file in order to avoid conflicts when overwriting original
            tmp = tempfile.TemporaryFile(mode="w+b")
            outpdf.write(tmp)
            outpdf.cloneDocumentFromReader(
                PyPDF2.PdfFileReader( tmp, strict = False ) )
    else:
        print("writing pdf to %s"%fn_out.encode(sys.getfilesystemencoding()))
    outpdf.write(open(fn_out.encode(sys.getfilesystemencoding()), "wb"))

def mendeley2pdf(fn_db, dir_pdf):
    db = sqlite3.connect(fn_db)
    highlights = get_highlights_from_db(db)
    annotations_all = get_notes_from_db(db, highlights)
    for fn, annons in annotations_all.items():
        try:
            fn_out = os.path.join(dir_pdf, os.path.basename(fn))
            if PRESERVE_TREE:
                #  only works together with --overwrite:
                #  overwrites, even if PDF in nested folder structure
                fn_out = fn
            print("Processing %s"%fn.encode(sys.getfilesystemencoding()))
            processpdf(fn, fn_out, annons)
        except PyPDF2.utils.PdfStreamError:
            print("I appear to have run out of things to join together on %s."%fn.encode(sys.getfilesystemencoding()))
            pass
        except PyPDF2.utils.PdfReadError:
            print("I appear to have run out of things to read on %s."%fn.encode(sys.getfilesystemencoding()))
            pass
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("mendeleydb", help="The mendeley sqlite database file",
                        type=str)
    parser.add_argument("dest", help="""The destination directory where to
                        save the annotated pdfs""", type=str)
    parser.add_argument("-w", "--overwrite", help="""Overwrite any PDF files in
                        the destination directory""", action="store_true")
    parser.add_argument("-p", "--preserve", help="""Preserves the original
                        directory tree together with --overwrite""",
                        action="store_true")
    args = parser.parse_args()
    fn = os.path.abspath(args.mendeleydb)
    dir_pdf = os.path.abspath(args.dest)
    if args.overwrite:
        OVERWRITE_PDFS = True
    if args.preserve:
        PRESERVE_TREE = True
    print("Mendeley database is expected to be encoded in UTF-8")
    print("Filesystem is encoded as %s."%sys.getfilesystemencoding())
    mendeley2pdf(fn, dir_pdf)
