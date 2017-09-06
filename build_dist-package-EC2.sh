sudo yum -y update
sudo yum -y upgrade
sudo yum -y groupinstall "Development Tools"
sudo yum -y install blas blas-devel lapack \
     lapack-devel Cython --enablerepo=epel

virtualenv pdenv
source pdenv/bin/activate
#pip install --upgrade pip
pip install pandas

for dir in lib64/python2.7/dist-packages \
             lib/python2.7/dist-packages
do
  if [ -d $dir ] ; then
    pushd $dir; zip -r ~/deps.zip .; popd
  fi
done

mkdir -p local/lib
cp /usr/lib64/liblapack.so.3 \
   /usr/lib64/libblas.so.3 \
   /usr/lib64/libgfortran.so.3 \
   /usr/lib64/libquadmath.so.0 \
   lib/
zip -r ~/deps.zip lib
cd app
zip -r ~/deps.zip *.py
