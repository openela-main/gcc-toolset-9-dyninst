# For RHEL8 we need this before using any scl macro.
%global __python /usr/bin/python3

%{?scl:%scl_package dyninst}

Summary: An API for Run-time Code Generation
License: LGPLv2+
Name: %{?scl_prefix}dyninst
Group: Development/Libraries
Release: 1%{?dist}
URL: http://www.dyninst.org
Version: 10.1.0
Exclusiveos: linux
ExclusiveArch: %{ix86} x86_64 ppc64le aarch64

Source0: https://github.com/dyninst/dyninst/archive/v%{version}/dyninst-%{version}.tar.gz
Source1: https://github.com/dyninst/testsuite/archive/v%{version}/testsuite-%{version}.tar.gz

Patch1: dyninst-10.1.0-tbb.patch
Patch2: dyninst-10.1.0-result.patch
Patch3: testsuite-10.1.0-386.patch

%global dyninst_base dyninst-%{version}
%global testsuite_base testsuite-%{version}


BuildRequires: zlib-devel
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: elfutils-devel
BuildRequires: elfutils-libelf-devel
BuildRequires: boost-devel
BuildRequires: binutils-devel
BuildRequires: cmake
BuildRequires: libtirpc-devel
BuildRequires: tbb tbb-devel

%{?scl:Requires: %scl_runtime}

# Extra requires just for the testsuite
# NB, there's no separate libstdc++-static for <=el6
%if 0%{?rhel} >= 7
BuildRequires: libstdc++-static
%endif
BuildRequires: gcc-gfortran glibc-static nasm libxml2-devel
%if 0%{?rhel} == 6
# C++11 requires devtoolset gcc.
BuildRequires: %{?scl_prefix}gcc-c++
%endif

# Testsuite files should not provide/require anything
%{?filter_setup:
%filter_provides_in %{_libdir}/dyninst/testsuite/
%filter_requires_in %{_libdir}/dyninst/testsuite/
%filter_setup
}

%description

Dyninst is an Application Program Interface (API) to permit the insertion of
code into a running program. The API also permits changing or removing
subroutine calls from the application program. Run-time code changes are
useful to support a variety of applications including debugging, performance
monitoring, and to support composing applications out of existing packages.
The goal of this API is to provide a machine independent interface to permit
the creation of tools and applications that use run-time code patching.

%package doc
Summary: Documentation for using the Dyninst API
Group: Documentation
%description doc
dyninst-doc contains API documentation for the Dyninst libraries.

%package devel
Summary: Header files for compiling programs with Dyninst
Group: Development/System
Requires: %{?scl_prefix}dyninst = %{version}-%{release}
Requires: boost-devel
Requires: tbb-devel

%description devel
dyninst-devel includes the C header files that specify the Dyninst user-space
libraries and interfaces. This is required for rebuilding any program
that uses Dyninst.

%package static
Summary: Static libraries for the compiling programs with Dyninst
Group: Development/System
Requires: %{?scl_prefix}dyninst-devel = %{version}-%{release}
%description static
dyninst-static includes the static versions of the library files for
the dyninst user-space libraries and interfaces.

%package testsuite
Summary: Programs for testing Dyninst
Group: Development/System
Requires: %{?scl_prefix}dyninst = %{version}-%{release}
Requires: %{?scl_prefix}dyninst-devel = %{version}-%{release}
Requires: %{?scl_prefix}dyninst-static = %{version}-%{release}
Requires: glibc-static
%description testsuite
dyninst-testsuite includes the test harness and target programs for
making sure that dyninst works properly.

%prep
%setup -q -n %{name}-%{version} -c
%setup -q -T -D -a 1

%patch1 -p1 -b.tbb
%patch2 -p1 -b.result
%patch3 -p1 -b.386

# cotire seems to cause non-deterministic gcc errors
# https://bugzilla.redhat.com/show_bug.cgi?id=1420551
sed -i.cotire -e 's/USE_COTIRE true/USE_COTIRE false/' \
  %{dyninst_base}/cmake/shared.cmake

%build

cd %{dyninst_base}

%if 0%{?rhel} == 6
# C++11 requires devtoolset gcc.
%{?scl:PATH=%{_bindir}${PATH:+:${PATH}}}
%endif

%cmake \
 -DENABLE_STATIC_LIBS=1 \
 -DCMAKE_BUILD_TYPE:STRING=None \
 -DINSTALL_LIB_DIR:PATH=%{_libdir}/dyninst \
 -DINSTALL_INCLUDE_DIR:PATH=%{_includedir}/dyninst \
 -DINSTALL_CMAKE_DIR:PATH=%{_libdir}/cmake/Dyninst \
 -DLIBDWARF_LIBRARIES:FILEPATH="$libdwarf_builddir/libdwarf.a;-lz" \
 -DLIBDWARF_INCLUDE_DIR:PATH=$libdwarf_builddir \
 -DBoost_NO_BOOST_CMAKE=ON \
 -DCMAKE_SKIP_RPATH:BOOL=YES
make %{?_smp_mflags}

# Hack to install dyninst nearby, so the testsuite can use it
make DESTDIR=../install install
find ../install -name '*.cmake' -execdir \
  sed -i -e 's!%{_prefix}!../install&!' '{}' '+'

cd ../%{testsuite_base}
%cmake \
 -DDyninst_DIR:PATH=$PWD/../install%{_libdir}/cmake/Dyninst \
 -DINSTALL_DIR:PATH=%{_libdir}/dyninst/testsuite \
 -DCMAKE_BUILD_TYPE:STRING=Debug \
 -DBoost_NO_BOOST_CMAKE=ON \
 -DCMAKE_SKIP_RPATH:BOOL=YES
make %{?_smp_mflags}

%install

cd %{dyninst_base}
make DESTDIR=$RPM_BUILD_ROOT install

# It doesn't install docs the way we want, so remove them.
# We'll just grab the pdfs later, directly from the build dir.
rm -v %{buildroot}%{_docdir}/*-%{version}.pdf

cd ../%{testsuite_base}
make DESTDIR=$RPM_BUILD_ROOT install

%files
%defattr(-,root,root,-)

%dir %{_libdir}/dyninst
%{_libdir}/dyninst/*.so.*
# dyninst mutators dlopen the runtime library
%{_libdir}/dyninst/libdyninstAPI_RT.so

%doc %{dyninst_base}/COPYRIGHT
%doc %{dyninst_base}/LICENSE.md

# %config(noreplace) /etc/ld.so.conf.d/*

%files doc
%defattr(-,root,root,-)
%doc %{dyninst_base}/dataflowAPI/doc/dataflowAPI.pdf
%doc %{dyninst_base}/dynC_API/doc/dynC_API.pdf
%doc %{dyninst_base}/dyninstAPI/doc/dyninstAPI.pdf
%doc %{dyninst_base}/instructionAPI/doc/instructionAPI.pdf
%doc %{dyninst_base}/parseAPI/doc/parseAPI.pdf
%doc %{dyninst_base}/patchAPI/doc/patchAPI.pdf
%doc %{dyninst_base}/proccontrol/doc/proccontrol.pdf
%doc %{dyninst_base}/stackwalk/doc/stackwalk.pdf
%doc %{dyninst_base}/symtabAPI/doc/symtabAPI.pdf

%files devel
%defattr(-,root,root,-)
%{_includedir}/dyninst
%{_libdir}/dyninst/*.so
%{_libdir}/cmake/Dyninst

%files static
%defattr(-,root,root,-)
%{_libdir}/dyninst/*.a

%files testsuite
%defattr(-,root,root,-)
%{_bindir}/parseThat

# Remove example tools packaged with dyninst
%exclude %{_bindir}/cfg_to_dot
%exclude %{_bindir}/codeCoverage
%exclude %{_bindir}/unstrip
%exclude %{_bindir}/ddb.db
%exclude %{_bindir}/params.db
%exclude %{_bindir}/unistd.db
# and the corresponding debuginfo
%exclude /usr/lib/debug/%{_bindir}/codeCoverage*debug
%exclude /usr/lib/debug/%{_bindir}/unstrip*debug

%dir %{_libdir}/dyninst/testsuite/
%attr(755,root,root) %{_libdir}/dyninst/testsuite/*[!a]
%attr(644,root,root) %{_libdir}/dyninst/testsuite/*.a

%changelog
* Sun Jun 9 2019 Stan Cox <scox@redhat.com> - 10.1.0-1
- Update to 10.1.0
