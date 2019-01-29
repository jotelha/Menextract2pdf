# Menextract2pdf
**Extract Mendeley annotations to PDF Files**

Menextract2pdf extracts highlights and notes from the Mendeley database and adds
them directly to all relevant PDF files, which can then be read by most PDF readers. 

## Why?

PDF highlights and notes in Mendeley are stored in the Mendeley database and can not
be read by other programs. While it is possible to extract and save the
annotations to the PDF file, this is a tedious manual process requiring to open
every PDF and selecting export to PDF for that file. Menextract2pdf provides
a bulk export functionality.
 
## Dependencies

Menextract2pdf is written in python2.7. It requires the following packages:
* PyPDF2
* sqlite3

It further incorporate (with small adjustments) the pdfannotation.py file from  the [PRSAnnots](https://github.com/rschroll/prsannots) project.

## Usage

```python
python menextract2pdf.py mendeley.sqlite /Destination/Dir/
```
where mendeley.sqlite is the mendeley database and /Destination/Dir/ is the
directory where to store the annotated PDF files. By default menextract2pdf
will not overwrite existing PDF files in the destination directory. To allow
overwriting use the ```--overwrite``` flag. 

The software is tested on Linux, but should run on Windows or Mac as well. 

## Migrating PDF from Mendeley to Zotero

Whith Mendeley 19, reference database is encrypted.

https://www.zotero.org/support/kb/mendeley_import suggests downgrading to Mendeley 18 in order to recover a decrypted database. In my case, that did not work out well: For some reason, Mendeley 18 got stuck on (re-)downloading the PDFs.

As an alternative, https://eighty-twenty.org/2018/06/13/mendeley-encrypted-db suggests a way on how to make Mendeley 19 decrypt its database, which worked for me. No second Mendeley installation or downgrading is necessary.

### Decrypt Mendeley database
First, decrypt Mendeley database following https://eighty-twenty.org/2018/06/13/mendeley-encrypted-db up until step 10 (relevant excerpt quoted below). Make a copy of the decrypted data base. 

Usually some file `{ENCODED_EMAIL_ADDRESS}@www.mendeley.com.sqlite` within `~/.local/share/data/Mendeley Ltd./Mendeley Desktop` holds the reference database

Quote from https://eighty-twenty.org/2018/06/13/mendeley-encrypted-db:

>  Quit Mendeley. You don’t want it running while you’re fiddling with its database.
> 
> BACK UP YOUR DATABASE. You will want to put things back the way they were after you’re done so you can use Mendeley
> again. THE REST OF THIS PROCEDURE MODIFIES THE DATABASE FILE ON DISK in ways that I do not know whether the Mendeley
> application can handle.
    
    cd ~/.local/share/data/Mendeley\ Ltd./Mendeley\ Desktop/
    cp b3616d71-0537-3d22-980d-c4eeb084e789@gmail.com@www.mendeley.com.sqlite ~/backup-encrypted.sqlite

> Start Mendeley under the control of gdb.

    mendeleydesktop --debug

> Add a breakpoint that captures the moment a SQLite database is opened.

    (gdb) b sqlite3_open_v2

> Start the program.

    (gdb) run

> The program will stop at the breakpoint several times. Keep continuing the program until the string pointed to by 
> `$rdi` names the file you backed up in the step above.

    Thread 1 "mendeleydesktop" hit Breakpoint 1, 0x000000000101b1b0 in sqlite3_open_v2 ()
    (gdb) x/s $rdi
    0x1dca928:	"/home/user/.local/share/data/Mendeley Ltd./Mendeley Desktop/Settings.sqlite"
    (gdb) c
    Continuing.

    Thread 1 "mendeleydesktop" hit Breakpoint 1, 0x000000000101b1b0 in sqlite3_open_v2 ()
    (gdb) x/s $rdi
    0x1dcb318:	"/home/tonyg/.local/share/data/Mendeley Ltd./Mendeley Desktop/Settings.sqlite"
    (gdb) c

    (… repeats a few times …)

    Thread 1 "mendeleydesktop" hit Breakpoint 1, 0x000000000101b1b0 in sqlite3_open_v2 ()
    (gdb) x/s $rdi
    0x25f1818:	"/home/user/.local/share/data/Mendeley Ltd./Mendeley Desktop/b3616d71-0537-3d22-980d-c4eeb084e789@gmail.com@www.mendeley.com.sqlite"

> Now, set a breakpoint for the moment the key is supplied to SEE. We don’t care about the key itself (for reasons
> discussed above), but we do care to find the moment just after sqlite3_key has returned.
```
(gdb) b sqlite3_key
Breakpoint 2 at 0x101b2c0
(gdb) c
Continuing.

Thread 1 "mendeleydesktop" hit Breakpoint 2, 0x000000000101b2c0 in sqlite3_key ()
(gdb) info registers 
rax            0x7fffffffc6b0	140737488340656
rbx            0x25f0590	39781776
rcx            0x7fffea9a0c40	140737129352256
rdx            0x20	32
rsi            0x260fd68	39910760
rdi            0x25ef4e8	39777512
rbp            0x7fffffffc730	0x7fffffffc730
rsp            0x7fffffffc688	0x7fffffffc688
r8             0xc1	193
r9             0x7fffea9a0cc0	140737129352384
r10            0x0	0
r11            0x1	1
r12            0x7fffffffc6b0	140737488340656
r13            0x7fffffffc6a0	140737488340640
r14            0x7fffffffc790	140737488340880
r15            0x7fffffffc790	140737488340880
rip            0x101b2c0	0x101b2c0 <sqlite3_key>
eflags         0x202	[ IF ]
cs             0x33	51
ss             0x2b	43
ds             0x0	0
es             0x0	0
fs             0x0	0
gs             0x0	0
```
> Copy down the value of $rdi from the info registers output. It is the pointer to the open SQLite database handle. > Then, finish execution of sqlite3_key.

    (gdb) fin
    Run till exit from #0  0x000000000101b2c0 in sqlite3_key ()
    0x0000000000f94e54 in SqliteDatabase::openInternal(QString const&, SqlDatabaseKey*) ()

> Use gdb’s ability to call C functions to rekey the database to the null key, thereby decrypting it in-place and 
> allowing Zotero import to do its work.

> Use the value for $rdi you noted down in the previous step as the first argument to sqlite3_rekey_v2, and zero 
> for the other three arguments.

    (gdb) p (int) sqlite3_rekey_v2(0x25ef4e8, 0, 0, 0)
    $1 = 0

> If you see $1 = 0 from the rekey command, all is well, and you may now use Zotero to import your Mendeley 
> database. 

> If your p sqlite3_rekey_v2(...) attempt fails, with (say) $1 = 8 as the outcome, then you may have been victim 
> of an unfortunate thread interleaving, or you might have caught a “spurious” opening of the database. It seems 
> that the program sometimes opens the main database at least once in some odd way, before opening it properly for
> long-term use.

> If you think it’s threading, you could try abandoning the procedure and restarting from the beginning: just quit
> gdb and restart the procedure from mendeleydesktop --debug.

> To deal with the “spurious” openings, experiment to see if the program opens the main database a second time. 
> Run the procedure all the way up to the p sqlite3_rekey_v2(...) step, but do not run sqlite3_rekey_v2. Instead, 
> just type c to continue, returning to the step where you inspect each call to sqlite3_open_v2, waiting for one 
> with $rdi pointing to a string with the right database filename. When you see it come round again, then try the 
> sqlite3_rekey_v2 step. If you see $1 = 0 this time, you’re all set, and can proceed as described above for a 
> successful call to sqlite3_rekey_v2.

This has been the case for me, the 2nd stop with $rdi pointing to the database file workde out.

> [...] leave gdb running and don’t touch it! DO NOT QUIT GDB OR RUN MENDELEY while the import 
> is proceeding. Who knows what might happen to your carefully decrypted database if you do!

> In fact, before you start Zotero, you might like to copy your decrypted database to somewhere safe, so you don’t
> have to do this again:

    cd ~/.local/share/data/Mendeley\ Ltd./Mendeley\ Desktop/
    cp b3616d71-0537-3d22-980d-c4eeb084e789@gmail.com@www.mendeley.com.sqlite ~/backup-decrypted.sqlite

You can browse the Mendeley data base now with a tool like http://sqlitebrowser.org, as recommended on
http://3.14a.ch/archives/2016/03/29/migrate-mendeley-library-and-keep-the-file-references/ for batch adjusting of PDF paths.

### Writing Mendeley annotations and highlighting from database to PDF

https://www.zotero.org/support/kb/mendeley_import suggests https://github.com/cycomanic/Menextract2pdf for batch annotation and highlighting export from the (decrypted) Mendeley database. A few modifications were necessary to

 * have it properly overwrite originals if in- and output PDF are the same
 * preserve a possible nested multilevel folder structure containing the PDF
 * handle exotic UTF-8 file names properly

implemented in a fork on https://github.com/jotelha/Menextract2pdf. Install 

    pip install PyPDF2 pysqlite python-dateutil

clone

    git clone git@github.com:jotelha/Menextract2pdf.git

and run

```bash
python2 Menextract2pdf/src/menextract2pdf.py ${DECRYPTED_DATABASE_FILE} ${PDF_OUTPUT_DIRECTORY} --overwrite --preserve
```

in order to embed annotations to PDFs. Attention: With `--overwrite` and `--preserve`, 
the original (possibly nested) folder structure is kept unchanged and original PDFs are overwritten by their annotated copies. In this case the `${PDF_OUTPUT_DIRECTORY}` does not matter, as all output is written to the original files.

### Mendeley Import in Zotero

Simply via "File" → "Import…" and choosing the "Mendeley" option. 

## Versions

* 0.1 first release

## Licence

The script is distributed under the GPLv3. The pdfannotations.py file is
LGPLv3. 

## Related projects

* [Mendeley2Zotero](https://github.com/flinz/mendeley2zotero)
* [Adios_Mendeley](https://github.com/rdiaz02/Adios_Mendeley)
