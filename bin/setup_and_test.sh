#!/bin/bash
set -xe
trap 'jobs -p | xargs --no-run-if-empty kill' INT TERM EXIT

export PATH=$PATH:/usr/local/bin
export PIP_DOWNLOAD_CACHE=~/.pip_cache

WD=`pwd`
POSTGRES_PORT=${POSTGRES_PORT:=5432}


echo "Downloading CKAN..."
git clone https://github.com/ckan/ckan


echo "Checking Solr..."
SOLR_ACTIVE=`nc -z localhost 8983; echo $?`

if [ $SOLR_ACTIVE -ne 0 ]
then
    
    echo "Downloading Solr..."
    CACHE_DIR=~/.cache
    FILE=solr-4.8.1.tgz
    SOLAR_UNZIP_FOLDER=solr-4.8.1

    # If the solar folder does not exist, we have to build it
    if [ ! -d "$CACHE_DIR/$SOLAR_UNZIP_FOLDER" ]
    then
        # Download the solar installation file if it does not exist
        if [ ! -f "$CACHE_DIR/$FILE" ]
        then
            wget --quiet --timestamping --directory-prefix=$CACHE_DIR http://apache.rediris.es/lucene/solr/4.8.1/$FILE
        fi

        # Unzip the folder
        tar -xf "$CACHE_DIR/$FILE" --directory "$CACHE_DIR"
    fi
    
    echo "Configuring and starting Solr..."
    ln -s "$CACHE_DIR/$SOLAR_UNZIP_FOLDER" .
    mv "$SOLAR_UNZIP_FOLDER/example/solr/collection1/conf/schema.xml"  "$SOLAR_UNZIP_FOLDER/example/solr/collection1/conf/schema.xml.bak"
    ln -s $WD/ckan/ckan/config/solr/schema.xml "$SOLAR_UNZIP_FOLDER/example/solr/collection1/conf/schema.xml"
    cd solr-4.8.1/example
    java -jar start.jar 2>&1 > /dev/null &
    cd $WD

else
    echo "Solar is already installed..."
fi


echo "Setting up virtualenv..."
virtualenv --no-site-packages virtualenv
source virtualenv/bin/activate
pip install --upgrade pip


echo "Installing CKAN dependencies..."
cd ckan
python setup.py develop
pip install -r requirements.txt --allow-all-external
pip install -r dev-requirements.txt --allow-all-external
cd ..


echo "Removing databases from old executions..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS datastore_test;"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ckan_test;"
sudo -u postgres psql -c "DROP USER IF EXISTS ckan_default;"


echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'
sudo -u postgres psql -c 'CREATE DATABASE datastore_test WITH OWNER ckan_default;'


echo "Modifying the configuration to setup properly the Postgres port..."
mkdir -p data/storage
echo "
sqlalchemy.url = postgresql://ckan_default:pass@localhost:$POSTGRES_PORT/ckan_test
ckan.datastore.write_url = postgresql://ckan_default:pass@localhost:$POSTGRES_PORT/datastore_test
ckan.datastore.read_url = postgresql://datastore_default:pass@localhost:$POSTGRES_PORT/datastore_test

ckan.storage_path=data/storage" >> test.ini


echo "Initializing the database..."
sed -i "s/\(postgresql:\/\/.\+@localhost\)/\1:$POSTGRES_PORT/g" ckan/test-core.ini 
cd ckan
paster db init -c test-core.ini
cd ..


echo "Installing ckanext-datastore-restful and its requirements..."
python setup.py develop
pip install -r dev-requirements.txt


echo "Running tests..."
nosetests --ckan --with-xunit --with-pylons=test.ini ckanext/datastore_restful/tests/ --with-coverage \
--cover-package=ckanext.datastore_restful --cover-inclusive --cover-erase . --cover-xml
