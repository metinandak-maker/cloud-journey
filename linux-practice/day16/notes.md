# Day 16 — Linux permissions
Date: 2026-10-14

## Permission values
r = read = 4
w = write = 2
x = execute = 1

Order: owner / group / others

600 = rw------- : owner reads and writes
660 = rw-rw---- : owner and group read and write
750 = rwxr-x--- : owner has all; group reads and executes
710 = rwx--x--- : owner has all; group only has execute

## Commands practised
chmod 600 secret.txt
chmod u+x hello.sh
chmod 750 hello.sh
chmod g+rx test-room
chmod g-r test-room
ls -l
ls -ld

## What I learned
A script needs execute permission to run using ./hello.sh.
For directories, x allows entry and traversal.
Directory r allows listing names.
Directory w usually needs x to create or delete entries.

## Practice location
/home/metin/linux-practice/permissions
Practice files are outside this Git repository.
