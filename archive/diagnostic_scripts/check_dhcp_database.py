#!/usr/bin/env python3
"""
Quick diagnostic script to check DHCP database entries for a specific device
"""
import sys
import pymysql

def check_dhcp_for_device(device_name):
    """Check DHCP database for a specific device"""
    
    # Connect to local MySQL via tunnel
    print(f"\nChecking DHCP database for device: {device_name}")
    print("="*80)
    
    try:
        # Connect to access database
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='access',
            password='44cC3sS',
            database='access',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✓ Connected to DHCP database (access)")
        
        # Check dhcpscope table
        cursor = conn.cursor()
        
        # Search by CMTS hostname
        print(f"\n1. Searching dhcpscope for CMTS: {device_name}")
        cursor.execute("""
            SELECT 
                scope, vlan, primary_subnet, cmts_hostname, cmts_interface, description
            FROM dhcpscope 
            WHERE cmts_hostname LIKE %s
            ORDER BY scope
        """, (f'%{device_name}%',))
        
        ipv4_scopes = cursor.fetchall()
        print(f"   Found {len(ipv4_scopes)} IPv4 DHCP scopes")
        
        if ipv4_scopes:
            for scope in ipv4_scopes[:20]:  # Show first 20
                print(f"   - {scope['scope']:18s} VLAN:{scope['vlan']:4d} Primary:{scope['primary_subnet']} Interface:{scope.get('cmts_interface', 'N/A')}")
            if len(ipv4_scopes) > 20:
                print(f"   ... and {len(ipv4_scopes) - 20} more")
        
        # Check primary subnets
        print(f"\n2. Unique primary subnets for {device_name}:")
        cursor.execute("""
            SELECT DISTINCT primary_subnet 
            FROM dhcpscope 
            WHERE cmts_hostname LIKE %s
        """, (f'%{device_name}%',))
        
        primaries = cursor.fetchall()
        for p in primaries:
            print(f"   - {p['primary_subnet']}")
        
        # Check IPv6 scopes
        print(f"\n3. Searching v6prefix for hostname: {device_name}")
        cursor.execute("""
            SELECT 
                prefixname, prefix, hostname, vlanid
            FROM v6prefix 
            WHERE hostname LIKE %s
            ORDER BY prefixname
        """, (f'%{device_name}%',))
        
        ipv6_scopes = cursor.fetchall()
        print(f"   Found {len(ipv6_scopes)} IPv6 prefixes")
        
        if ipv6_scopes:
            for scope in ipv6_scopes[:20]:  # Show first 20
                print(f"   - {scope['prefixname']:30s} {scope['prefix']:20s} VLAN:{scope.get('vlanid', 'N/A')}")
            if len(ipv6_scopes) > 20:
                print(f"   ... and {len(ipv6_scopes) - 20} more")
        
        # Summary
        print(f"\n" + "="*80)
        print(f"SUMMARY for {device_name}:")
        print(f"  - IPv4 DHCP Scopes: {len(ipv4_scopes)}")
        print(f"  - IPv6 DHCP Prefixes: {len(ipv6_scopes)}")
        print(f"  - Total DHCP Entries: {len(ipv4_scopes) + len(ipv6_scopes)}")
        
        if len(ipv4_scopes) == 0 and len(ipv6_scopes) == 0:
            print(f"\n⚠️  NO DHCP ENTRIES FOUND for {device_name}")
            print(f"    Possible reasons:")
            print(f"    1. Device name doesn't match exactly in DHCP database")
            print(f"    2. DHCP scopes are registered under a different hostname")
            print(f"    3. Device doesn't have DHCP configured yet")
            
            # Try fuzzy search
            print(f"\n4. Trying fuzzy search for similar hostnames...")
            search_pattern = f'%{device_name[:6]}%'  # First 6 chars
            cursor.execute("""
                SELECT DISTINCT cmts_hostname 
                FROM dhcpscope 
                WHERE cmts_hostname LIKE %s
                LIMIT 10
            """, (search_pattern,))
            
            similar = cursor.fetchall()
            if similar:
                print(f"   Similar hostnames found in dhcpscope:")
                for s in similar:
                    print(f"   - {s['cmts_hostname']}")
            else:
                print(f"   No similar hostnames found")
        
        cursor.close()
        conn.close()
        print("="*80)
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        print("  Make sure the SSH tunnel is running: ./ssh-tunnel.sh start")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_dhcp_database.py <device_name>")
        print("Example: python check_dhcp_database.py ad00cbr67")
        sys.exit(1)
    
    device_name = sys.argv[1]
    check_dhcp_for_device(device_name)
