## INITIATING CHANGES FOR DJANGO SETUP

### Step 1

Create virtual environment

`python3 -m venv .venv`

### Step 2

Enter into virtual environment

> OS / What their user think they are / What they actually are

Windows / Gamers / Gareeb

`./.venv/Scripts/activate`


Linux / Heckerman / Gareeb

`source .venv/bin/activate`

MacOS / diladu tenu burz khalifa / Gareeb (Mac se ameer nhi bante)

`source .venv/bin/activate`

> A (.venv) should appear beside your command line prompt

### Step 3

Run migrations

`python3 manage.py migrate`

### Step 4

Start. finally

`python3 manage.py runserver`

---

## Changes that will be repeated for all apps

> /communications is already done, follow that

### Step 1

Update the already present `<app>/views.py`

### Step 2

Create urls file `<app>/urls.py`

### Step 3

Import the views in `config/urls.py`

