wget https://www.python.org/ftp/python/3.6.8/Python-3.6.8.tgz
tar xvf Python-3.6.8.tgz
cd Python-3.6.8
./configure --enable-optimizations
make -j8
sudo make altinstall
