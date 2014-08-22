from django.shortcuts import render_to_response, HttpResponse
from django.http import HttpResponseRedirect
from django.template import RequestContext

from servers.models import Compute
from instance.models import Instance
from servers.forms import ComputeAddTcpForm, ComputeAddSshForm, ComputeEditHostForm, ComputeAddTlsForm
from vrtManager.hostdetails import wvmHostDetails
from vrtManager.connection import CONN_SSH, CONN_TCP, CONN_TLS, connection_manager
from libvirt import libvirtError


def index(request):
    """

    Index page.

    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')
    else:
        return HttpResponseRedirect('/servers')
    
def connection_debug(request):
    '''
    outputs connection debug info
    '''
    html = '<html><head><title>Connection Debug</title></head><body>'
    
    import time, os, threading
    html += '<h1>Connection Debug</h1><br /><dl>'
    
    html += '<dt>Process ID:</dt>'
    html += '<dd>' + str(os.getpid()) + '</dd>'
    
    html += '<dt>Process ID:</dt>'
    html += '<dd>' + str(threading.current_thread()) + '</dd>'
    
    html += '</dl><br />'
    
    for host, connections in connection_manager._connections.iteritems():
        for connection in connections:
            html += '<h2>' + str(connection) + '</h2>'
            html += '<dl>'
            
            html += '<dt>Host Key:</dt>'
            html += '<dd>' + repr(host) + '</dd>'
            
            html += '<dt>Connection Status:</dt>'
            html += '<dd>' + ('Connected' if connection.connected else 'Disconnected') + '</dd>'
            
            html += '<dt>Last Error:</dt>'
            html += '<dd>' + str(connection.last_error) + '</dd>'
            
            html += '<dt>Use Count:</dt>'
            html += '<dd>' + (str(connection.use_count) if hasattr(connection, 'use_count') else '---') + '</dd>'
            
            html += '<dt>Uptime:</dt>'
            html += '<dd>' + (str(time.time() - connection.connection_time) if hasattr(connection, 'connection_time') and connection.connection_time is not None else '---') + '</dd>'
            
            html += '</dl>'
            html += '<br />' 
    
    html += '</body></html>'
    return HttpResponse(html)


def servers_list(request):
    """
    Servers page.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')

    def get_hosts_status(hosts):
        """
        Function return all hosts all vds on host
        """
        all_hosts = []
        for host in hosts:
            if (connection_manager.host_is_up(host.hostname, host.login, host.password, host.type)):
                status = 1
            else:
                status = 'Unknown Error'
                
            all_hosts.append({'id': host.id,
                              'name': host.name,
                              'hostname': host.hostname,
                              'status': status,
                              'type': host.type,
                              'login': host.login,
                              'password': host.password
                              })
        return all_hosts

    computes = Compute.objects.filter()
    hosts_info = get_hosts_status(computes)
    form = None

    if request.method == 'POST':
        if 'host_del' in request.POST:
            compute_id = request.POST.get('host_id', '')
            try:
                del_inst_on_host = Instance.objects.filter(compute_id=compute_id)
                del_inst_on_host.delete()
            finally:
                del_host = Compute.objects.get(id=compute_id)
                del_host.delete()
            return HttpResponseRedirect(request.get_full_path())
        if 'host_tcp_add' in request.POST:
            form = ComputeAddTcpForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                new_tcp_host = Compute(name=data['name'],
                                       hostname=data['hostname'],
                                       type=CONN_TCP,
                                       login=data['login'],
                                       password=data['password'])
                new_tcp_host.save()
                return HttpResponseRedirect(request.get_full_path())
        if 'host_ssh_add' in request.POST:
            form = ComputeAddSshForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                new_ssh_host = Compute(name=data['name'],
                                       hostname=data['hostname'],
                                       type=CONN_SSH,
                                       login=data['login'])
                new_ssh_host.save()
                return HttpResponseRedirect(request.get_full_path())
        if 'host_tls_add' in request.POST:
            form = ComputeAddTlsForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                new_tls_host = Compute(name=data['name'],
                                       hostname=data['hostname'],
                                       type=CONN_TLS,
                                       login=data['login'],
                                       password=data['password'])
                new_tls_host.save()
                return HttpResponseRedirect(request.get_full_path())

        if 'host_edit' in request.POST:
            form = ComputeEditHostForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                compute_edit = Compute.objects.get(id=data['host_id'])
                compute_edit.name = data['name']
                compute_edit.hostname = data['hostname']
                compute_edit.login = data['login']
                compute_edit.password = data['password']
                compute_edit.save()
                return HttpResponseRedirect(request.get_full_path())

    return render_to_response('servers.html', locals(), context_instance=RequestContext(request))


def infrastructure(request):
    """
    Infrastructure page.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')

    compute = Compute.objects.filter()
    hosts_vms = {}

    for host in compute:
        if connection_manager.host_is_up(host.hostname, host.login, host.password, host.type):
            try:
                conn = wvmHostDetails(host, host.login, host.password, host.type)
                host_info = conn.get_node_info()
                host_mem = conn.get_memory_usage()
                hosts_vms[host.id, host.name, 1, host_info[3], host_info[2],
                          host_mem['percent']] = conn.get_host_instances()
                conn.close()
            except libvirtError:
                hosts_vms[host.id, host.name, 3, 0, 0, 0] = None
        else:
            hosts_vms[host.id, host.name, 2, 0, 0, 0] = None

    return render_to_response('infrastructure.html', locals(), context_instance=RequestContext(request))
