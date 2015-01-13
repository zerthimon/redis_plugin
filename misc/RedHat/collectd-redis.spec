# This is python script actually, so we use serial for versioning
%define build_timestamp %(date +"%Y%m%d")

Name:          collectd-redis
Version:       0.0.%{build_timestamp}
Release:       1%{?dist}
Summary:       Collectd plugin to populate statistics from redis (written in python)

Group:         System Environment/Daemons
License:       GPLv2
URL:           https://github.com/zerthimon/redis_plugin
Source0:       collectd-redis.tar.gz
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:      collectd-python

%description
Collectd plugin to populate statistics from redis (written in python)

%prep
%setup -q -n collectd-redis
%build
%install
install -m 0755 -d $RPM_BUILD_ROOT%{_datadir}/collectd/plugins
install -m 0755 redis_plugin.py $RPM_BUILD_ROOT%{_datadir}/collectd/plugins/redis_plugin.py
install -m 0755 redis_types.db $RPM_BUILD_ROOT%{_datadir}/collectd/redis_types.db

%clean
rm -rf $RPM_BUILD_ROOT

%files
%dir %{_datadir}/collectd/plugins
%{_datadir}/collectd/plugins/redis_plugin.py*
%{_datadir}/collectd/redis_types.db

%defattr(-,root,root,-)
%doc

%changelog
* Tue Dec 15 2014 Denis Boulas <dene14@gmail.com>
- Initial build.
