# Twitter Archive Browser: Take back your DMs

View the demo [here](https://messageviewerdemo.mitch.website/conversation/messages/1).

Twitter allows you to download zip files containing all of the data that it has ever collected on you, but tragically, that data is then trapped inside huge .js files with esoteric schema and unapproachable documentation. This project aims to fix that; it can parse the huge files, save their contents to an easily browsable on-disk database, and then display them through your web browser in a client that rivals the experience of the best messaging apps like Discord.

This project is currently focused on displaying messages (both direct and group) since those are currently the least easily untangled from the archive and the hardest to search on Twitter itself, but ideally it will be someday expanded to display and search your Tweets and likes as well.

## Installation

### Python

This project does most of its work with Python 3.9; even if you already have Python, make sure you have at least that version [here](https://www.python.org/downloads/release/python-390/). Note: if you are building Python from source, you might have to download the libsqlite3 or sqlite-devel packages so that Python can build with the required sqlite3 support; otherwise, if you are using e. g. the Windows installer, you should be good to go.

### Various Python Libraries

The Python libraries that this project uses are managed by pipenv; after installing Python, you should be able to install pipenv by running the command `pip install --user pipenv` anywhere. You can then install said libraries by navigating your command line to this folder and running `pipenv install`.

### NPM (optional)

To compile the JSX code that lays out the template for the browser interface into JavaScript, this project uses webpack and a few other libraries managed by NPM; however, you don't have to install NPM if you are downloading the code from the "releases" section to the right, as that includes the compiled JavaScript bundle. If you do want to compile this code yourself, download NPM from your OS's package manager or from [here](https://www.npmjs.com/get-npm), run the command `npm install` in this folder, and then run the command `npx webpack` to produce a bundle (it will be located in the path /frontend/assets/js.) You can also run webpack once every time you start the main program with the option `--mode single_build` or run it continuously as you make changes with `--mode dev`.

## Running it

First, navigate your command line interface to this folder and enter the command `pipenv shell` to access the packages that pipenv installed earlier, in the installation section.

The main thing that this program needs is the path to the "data" folder from your unzipped Twitter archive; you can run it if you want just by entering `python main.py /path/to/data`. Your archive data can be enhanced by downloading the usernames and avatars of each user who appears in your messages if you give the program a bearer token that will let it download information from Twitter, subject to certain limits that no one instance of this program should ever brush up against; you can get one from Twitter easily (more easily than they make it sound) [here](https://developer.twitter.com/en/apply-for-access) (or if you happen to know me, you can ask to use mine.) With that in place, the command line invocation becomes `python main.py /path/to/data -b PUTYOURTOKENHERE`. If you're running this program while connected to a network where people spy on each other regularly or if you want to make your archive available to some people over the open Internet, you can secure it with a password with the -pw option `python main.py /path/to/data -b PUTYOURTOKENHERE -pw PUTPASSWORDHERE`; if for similar reasons you want it to run on a specific network port, you can enter that with the -po option (figure it out.)

After all that, the full command line options are here:

```
usage: main.py [-h] [-b BEARER_TOKEN] [-o] [-pw PASSWORD] [-po PORT]
               [-m {dev,single_build,no_build}]
               path_to_data

Load messages from a Twitter data archive and display them via a web client.
The loaded messages will be placed in a .db file in the db folder in this
directory; you can then navigate your browser to the web client, which will
display them analytically and elegantly.

positional arguments:
  path_to_data          The path of the "data" folder from your unzipped
                        Twitter data archive. This will be something like
                        ../twitterarchive/data or
                        "C:/Users/Jim/Downloads/Twitter Archive/data"

optional arguments:
  -h, --help            show this help message and exit
  -b BEARER_TOKEN, --bearer_token BEARER_TOKEN
                        A bearer token obtained from the Twitter developer
                        portal; used to download data on the users that appear
                        in this archive. This can be either the token itself
                        or a path to a JSON file with a 'bearer_token' field.
                        If this is not supplied, users will be identified only
                        with numbers (although you can then go through and
                        give them nicknames for the purposes of viewing the
                        archive.) This is only needed when creating a
                        database; if you're invoking this command later to re-
                        start the web client, ignore this.
  -o, --overwrite       This flag causes any existing database generated for
                        an account with this program to be overwritten with a
                        newly-created database. Use this option if, for
                        example, you initially created the database without
                        user data being fetched and you want to create a new
                        database while supplying a bearer token.
  -pw PASSWORD, --password PASSWORD
                        A password that anyone who navigates to the web client
                        will be required to enter. This password will not be
                        saved; it must be re-entered each time you run this
                        program.
  -po PORT, --port PORT
                        The port that your data will be served from. If
                        unsure, ignore this and just go to the localhost url
                        that appears after starting the program to view your
                        archive.
  -m {dev,single_build,no_build}, --mode {dev,single_build,no_build}
                        Set this flag to "dev" if you plan on editing the
                        frontend code and want it to be continuously rebuild,
                        "single_build" if you need the frontend to be built
                        once so that you can use it, and "no_build" (the
                        default) if you are using a pre-made main.js bundle
                        from a release.
```

## Contributing

I don't know how this works, but please do. Note: the tests are currently a mess.
