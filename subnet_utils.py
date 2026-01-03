#!/usr/bin/env python3
"""
Subnet Utilities
=================

Helper functions for subnet validation and filtering.
Distinguishes between public and private IP addresses.

Author: Silvester van der Leer
"""

import ipaddress
from typing import List


def is_public_ipv4(subnet: str) -> bool:
    """
    Check if an IPv4 subnet is public (routable on the internet).
    
    Returns False for:
    - Private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Loopback (127.0.0.0/8)
    - Link-local (169.254.0.0/16)
    - Multicast (224.0.0.0/4)
    - Reserved ranges
    
    Args:
        subnet: IPv4 subnet in CIDR notation (e.g., "203.80.0.0/22")
    
    Returns:
        True if public, False if private/reserved
    """
    try:
        network = ipaddress.IPv4Network(subnet, strict=False)
        return not (
            network.is_private or
            network.is_loopback or
            network.is_link_local or
            network.is_multicast or
            network.is_reserved
        )
    except (ValueError, ipaddress.AddressValueError):
        return False


def is_public_ipv6(subnet: str) -> bool:
    """
    Check if an IPv6 subnet is public (globally routable).
    
    Returns False for:
    - Private/ULA ranges (fc00::/7)
    - Link-local (fe80::/10)
    - Loopback (::1/128)
    - Multicast (ff00::/8)
    
    Args:
        subnet: IPv6 subnet in CIDR notation (e.g., "2001:db8:100::/40")
    
    Returns:
        True if public, False if private/reserved
    """
    try:
        network = ipaddress.IPv6Network(subnet, strict=False)
        return not (
            network.is_private or
            network.is_loopback or
            network.is_link_local or
            network.is_multicast or
            network.is_reserved
        )
    except (ValueError, ipaddress.AddressValueError):
        return False


def is_public_subnet(subnet: str) -> bool:
    """
    Check if a subnet (IPv4 or IPv6) is public.
    
    Args:
        subnet: Subnet in CIDR notation
    
    Returns:
        True if public, False if private/reserved
    """
    if ':' in subnet:
        return is_public_ipv6(subnet)
    else:
        return is_public_ipv4(subnet)


def filter_public_subnets(subnets: List[str]) -> List[str]:
    """
    Filter a list of subnets to include only public ones.
    
    Args:
        subnets: List of subnets in CIDR notation
    
    Returns:
        List containing only public subnets
    """
    return [subnet for subnet in subnets if is_public_subnet(subnet)]


def categorize_subnets(subnets: List[str]) -> dict:
    """
    Categorize subnets into public and private.
    
    Args:
        subnets: List of subnets in CIDR notation
    
    Returns:
        Dictionary with 'public' and 'private' keys containing lists
    """
    public = []
    private = []
    
    for subnet in subnets:
        if is_public_subnet(subnet):
            public.append(subnet)
        else:
            private.append(subnet)
    
    return {
        'public': public,
        'private': private
    }


if __name__ == "__main__":
    """Test subnet utilities"""
    print("Subnet Utilities Test\n")
    
    test_subnets = [
        # IPv4 private
        "10.1.0.0/24",
        "172.16.0.0/22",
        "192.168.1.0/24",
        # IPv4 public
        "203.80.0.0/22",
        "198.51.100.0/24",
        "8.8.8.0/24",
        # IPv6 public
        "2001:db8:100::/40",
        "2001:4860::/32",
        # IPv6 private
        "fc00::/7",
        "fe80::/10"
    ]
    
    print("Testing subnet classification:\n")
    for subnet in test_subnets:
        is_public = is_public_subnet(subnet)
        status = "PUBLIC" if is_public else "PRIVATE"
        print(f"  {subnet:25} -> {status}")
    
    print("\n✓ Public subnets only:")
    public_only = filter_public_subnets(test_subnets)
    for subnet in public_only:
        print(f"  - {subnet}")
    
    print("\n✅ All tests completed!")
