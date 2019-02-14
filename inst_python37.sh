wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tgz
tar xvf Python-3.7.2.tgz
cd Python-3.7.2
./configure --enable-optimizations
make -j8
sudo make altinstall
