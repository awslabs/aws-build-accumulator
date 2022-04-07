Contributing
============

Thank you for contributing to Litani! This document collects some coding and
process guidelines.


### HTML Dashboard

- Please test your changes with both light and dark mode, and with a range of
  browser widths.
- Almost all top-level divs should have an id attribute; this makes it easy to
  link to specific information.
- We prefer to inline all assets (CSS, images) onto the page so that it's easy
  to send single, self-contained pages around. For this reason, please try to
  keep SVGs small.


## Releases

Major releases are done through the `scripts/release` script. Patch releases are
still manual.

### Creating a patch release

#### Summary

- Write the patch on top of `develop` as normal, and open a PR to get it merged
  into `develop`.
- Once it's merged into `develop`, cherry-pick the commits onto a new branch
  called `backport`.
- Add a commit to `backport`, on top of the fixes, that updates the changelog
  with the fix information.
- Merge `release` into `backport` using a merge commit.

#### Process

Suppose you’re in the current state:

```
; git log --graph  --decorate --date=relative --format=format:'%C(green)%h%C(yellow) %s%C(reset)%w(0,6,6)%C(bold green)\n  %C(bold red)%aN%C(reset) %cr%C(reset)%w(0,0,0)\n%-D\n%C(reset)' --all

* c59fc53 add foobar
| HEAD -> develop
|
* 139191f implement feature
|
*   d6f2fa0 Release 1.2.0
|\  tag: 1.2.0, release
| |
| * f3ff462 add script
```

To add a fix to the `release` branch, first create it on top of `develop`. Go
through the code review process to get it merged into develop as normal.

```
; git log --graph  --decorate --date=relative --format=format:'%C(green)%h%C(yellow) %s%C(reset)%w(0,6,6)%C(bold green)\n  %C(bold red)%aN%C(reset) %cr%C(reset)%w(0,0,0)\n%-D\n%C(reset)' --all

*  bbb222 Create two-part fix
|  HEAD -> develop
|\
| * c59fc53 Important Fix Part 2
| |
| * ef45678 Important Fix Part 1
|/
* abcd123 add foobar
|
* 139191f implement feature
|
*   d6f2fa0 Release 1.2.0
|\  tag: 1.2.0, release
| |
```

Then check out `release`; check out a new branch called `backport`; and
cherry-pick only the commits you need onto the `backport` branch. You can use
git-log to check which commits you’re about to transplant. If there are
conflicts, you will need to resolve and commit them one at a time until the
graph looks the way you expect (below).

```
; git log --pretty=%h c59fc53..develop
abcd123
ef45678
; git checkout release
; git checkout -b backport
; git cherry-pick c59fc53..develop
; git log --graph  --decorate --date=relative --format=format:'%C(green)%h%C(yellow) %s%C(reset)%w(0,6,6)%C(bold green)\n  %C(bold red)%aN%C(reset) %cr%C(reset)%w(0,0,0)\n%-D\n%C(reset)' --all

* αβγ321 Important Fix Part 2
| HEAD -> backport
|
* zyx765 Important Fix Part 1
|
| *  bbb222 Create two-part fix
| |  develop
| |\
| | * c59fc53 Important Fix Part 2
| | |
| | * ef45678 Important Fix Part 1
| |/
| * c59fc53 add foobar
| |
| * 139191f implement feature
| |
|/
*   d6f2fa0 Release 1.2.0
|\  tag: 1.2.0, release
| |
```

Finally, merge the release branch into `backport`. Currently, doing a major
release after having done a minor one might require manual tweaking.

```
; git checkout release
; git merge --no-ff backport
; git log --graph  --decorate --date=relative --format=format:'%C(green)%h%C(yellow) %s%C(reset)%w(0,6,6)%C(bold green)\n  %C(bold red)%aN%C(reset) %cr%C(reset)%w(0,0,0)\n%-D\n%C(reset)' --all

*   fff000 Bump version to 1.3.0
|   HEAD -> release, backport, tag: 1.3.0
|\
| *   αβγ321 Important Fix Part 2
| |
| *   zyx765 Important Fix Part 1
| |
| |  * ef45678 Important Fix Part 2
| |  | develop
| |  |
| |  * abcd123 Important Fix Part 1
| |  |
| |  * c59fc53 add foobar
| |  |
| |  * 139191f implement feature
| |  |
| | /
|/ /
| /
|/
*   d6f2fa0 Release 1.2.0
|\  tag: 1.2.0
| |
```
