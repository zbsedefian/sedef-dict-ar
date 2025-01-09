# SedefDict - Arabic Dictionary and Morphology Analyzer

## About

One of the more difficult tasks for beginner and intermediate students of Arabic is dictionary usage.

Dictionary lookups can take minutes. Classical Arabic dictionaries are formatted not in an alphabetical order, but an order primarily dependent on word root.

Arabic word formation mostly relies on derivations from a triliteral or quadriliteral consonantal root. That means the word of the verb /kataba/ 'to write' is [k, t, b]. This system forms the basis for many other words, like /maktab/ "office, desk", /kaatib/ "writer", and innumerable more.

This application attempts to break down the barrier to entry for modern students. While physical dictionary lookups can be rewarding, if we are practicing intensive reading, sometimes we just want to get the definition immediately.

## Run

`uvicorn arabic_dict_app:app --reload`

or

`docker-compose use --build`

## Deploy

`./build-and-deploy.sh`